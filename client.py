import pandas as pd
import json
import pyarrow as pa
from pyarrow.flight import FlightClient, Ticket


if __name__ == "__main__":
    client = FlightClient(
        location="grpc://localhost:8815",
    )

    query = "MATCH (n) RETURN n"
    schema = pa.schema([
        pa.field("id", pa.int64()),
        pa.field("name", pa.string()),
    ])

    schema_json = [{"name": field.name, "type": str(field.type)} for field in schema]
    ticket_payload = {
        "query": query,
        "schema": schema_json,
    }

    ticket = Ticket(json.dumps(ticket_payload).encode("utf-8"))
    reader = client.do_get(ticket, None)

    table = reader.read_all()
    df = table.to_pandas()

    print(df.head())