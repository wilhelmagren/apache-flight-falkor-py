import argparse
import json
import pyarrow as pa
from typing import Iterable
from pyarrow.flight import (
    FlightServerBase,
    ServerCallContext,
    Ticket,
)
import requests

class FlightServer(FlightServerBase):
    def __init__(
        self,
        flight_port: str,
        falkordb_host: str,
        falkordb_port: str,
    ):
        """"""
        super(FlightServer, self).__init__(
            location=f"grpc://0.0.0.0:{flight_port}",
        )
        self._falkordb_host = falkordb_host
        self._falkordb_port = falkordb_port
        self._falkordb_url = f"http://{self._falkordb_host}:{self._falkordb_port}"

    def do_get(
        self,
        context: ServerCallContext,
        ticket: Ticket,
    ) -> pa.RecordBatchReader:
        """Handle a GET request."""
        payload = json.loads(ticket.ticket.decode("utf-8"))
        query = payload["query"]
        schema_json = payload["schema"]
        schema = pa.schema(
            [pa.field(**field) for field in schema_json]
        )

        # TODO: send auth token in header to FalkorDB also?
        response = requests.post(
            f"{self._falkordb_url}/query",
            json={"cypher": query},
        )
        response.raise_for_status()

        result = response.json()
        data = [
            pa.array(result["data"].get(f), type=f.type)
            for f in schema
        ]
        table = pa.Table.from_arrays(data, schema=schema)
        batches = table.to_batches()
        return pa.flight.RecordBatchReader.from_batches(
            schema=schema,
            batches=batches,
        )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Apache Arrow Flight server for FalkorDB."
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

    args = parser.parse_args()

    flight_port = args.flight_port
    falkordb_host = args.falkordb_host
    falkordb_port = args.falkordb_port

    server = FlightServer(
        flight_port=flight_port,
        falkordb_host=falkordb_host,
        falkordb_port=falkordb_port,
    )
    print(f"Starting Arrow Flight server on port {flight_port}...")
    server.serve()
