import argparse
import pyarrow as pa
from typing import Optional
from pyarrow.flight import (
    FlightServerBase,
    ServerCallContext,
    Ticket,
)
import requests

class MTLSFlightServer(FlightServerBase):
    def __init__(
        self,
        flight_port: str,
        falkordb_host: str,
        falkordb_port: str,
        cert_chain: str,
        private_key: str,
        root_certs: Optional[str] = None,
    ):
        """"""
        super(MTLSFlightServer, self).__init__(
            location=f"grpc+tls://0.0.0.0:{flight_port}",
            verify_client=True,
            tls_certificates=[(cert_chain, private_key)],
            root_certificates=root_certs,
        )
        self._falkordb_host = falkordb_host
        self._falkordb_port = falkordb_port
        self._falkordb_url = f"http://{self._falkordb_host}:{self._falkordb_port}"

    def do_get(
        self,
        context: ServerCallContext,
        ticket: Ticket,
        schema: pa.Schema,
    ) -> pa.RecordBatchReader:
        """Handle a GET request."""
        query = ticket.ticket.decode("utf-8")

        # TODO: send auth token in header to FalkorDB also?
        response = requests.post(
            f"{self._falkordb_url}/query",
            json={"cypher": query},
        )
        response.raise_for_status()

        result = response.json()
        data = [
            pa.array(result["data"][c])
            for c in schema.names
        ]
        table = pa.Table.from_arrays(data, schema=schema)
        batches = table.to_batches()
        return pa.flight.RecordBatchReader.from_batches(
            schema=schema,
            batches=batches,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apache Arrow Flight server for FalkorDB with mTLS authentication."
    )

    parser.add_argument(
        "--flight-port",
        type=str,
        default=8815,
        help="The port to use for the Flight server (default: 8815)."
    )
    parser.add_argument(
        "--falkordb-host",
        type=str,
        required=True,
        help="The FalkorDB hostname."
    )
    parser.add_argument(
        "--falkordb-port",
        type=str,
        default=8080,
        help="The FalkorDB port (default: 8080)."
    )
    parser.add_argument(
        "--cert-chain",
        type=str,
        required=True,
        help="Path to the certificate chain file.",
    )

    parser.add_argument(
        "--private-key",
        type=str,
        required=True,
        help="Path to the private key file.",
    )

    parser.add_argument(
        "--root-certs",
        type=str,
        default=None,
        help="Path to the root certificates file (optional).",
    )

    args = parser.parse_args()

    flight_port = args.flight_port
    falkordb_host = args.falkordb_host
    falkordb_port = args.falkordb_port
    cert_chain = args.cert_chain
    private_key = args.private_key
    root_certs = args.root_certs

    server = MTLSFlightServer(
        flight_port=flight_port,
        falkordb_host=falkordb_host,
        falkordb_port=falkordb_port,
        cert_chain=cert_chain,
        private_key=private_key,
        root_certs=root_certs,
    )

    print(f"Starting mTLS Arrow Flight server on port {flight_port}...")
    server.serve()
