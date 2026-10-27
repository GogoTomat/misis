from schema import schema_batched, DB_CALLS

QUERY = """
{
  orders {
    id
    status
    user {
      name
    }
  }
}
"""


def main():
    DB_CALLS["count"] = 0
    result = schema_batched.execute(QUERY)
    print("Errors:", result.errors)
    print("Orders returned:", len(result.data["orders"]))
    print("Total DB calls:", DB_CALLS["count"])


if __name__ == "__main__":
    main()
