import pandas as pd
from pyarrow.flight import FlightClient, Ticket


if __name__ == "__main__":
    # Paths to the client certificate, private key, and CA certificate
    client_cert_path = "client_cert.pem"
    client_key_path = "client_key.pem"
    ca_cert_path = "ca_cert.pem"

    client = FlightClient(
        location="grpc+tls://localhost:8815",
        tls_root_certs=ca_cert_path,
        cert_chain=client_cert_path,
        private_key=client_key_path
    )

    query = "MATCH (n) RETURN n"

    ticket = Ticket(query.encode("utf-8"))
    reader = client.do_get(ticket)

    table = reader.read_all()
    df = table.to_pandas()

    print(df.head())