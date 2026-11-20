import json
import requests

def zoek_in_termennetwerk(keyword, timeout_ms=15000, only_available=True):
    """
    Search every Network of Terms source for a keyword.
    Returns a list of dicts: {"uri", "name", "description", "source"}.
    """
    endpoint = "https://termennetwerk-api.netwerkdigitaalerfgoed.nl/graphql"

    def gql(query):
        r = requests.post(endpoint, json={"query": query}, timeout=90)
        r.raise_for_status()
        data = r.json()
        if "errors" in data:
            raise RuntimeError(data["errors"])
        return data["data"]

    # Step 1: get all source URIs
    sources = gql("query { sources { uri status { isAvailable } } }")["sources"]
    if only_available:
        # status is null when a source hasn't been checked yet, so keep those
        sources = [s for s in sources if not s["status"] or s["status"]["isAvailable"]]
    uris = [s["uri"] for s in sources]

    # Step 2: search all sources at once
    query = f"""
    query {{
      terms(
        sources: {json.dumps(uris)},
        query: {json.dumps(keyword)},
        timeoutMs: {timeout_ms}
      ) {{
        source {{ name }}
        result {{
          ... on Terms {{
            terms {{
              uri
              prefLabel
              definition
              scopeNote
            }}
          }}
          ... on Error {{
            message
          }}
        }}
      }}
    }}
    """

    items = []
    for source_result in gql(query)["terms"]:
        result = source_result["result"]
        if "terms" not in result:  # source returned an Error (e.g. timeout), skip it
            continue
        for term in result["terms"]:
            # label/definition fields are lists of strings, so join them
            description = term.get("definition") or term.get("scopeNote") or []
            items.append({
                "uri": term["uri"],
                "name": "; ".join(term.get("prefLabel") or []),
                "description": " ".join(description),
                "source": source_result["source"]["name"],
            })
    return items


# Example
if __name__ == "__main__":
    termen = zoek_in_termennetwerk("Donners")
    for term in termen:
        print(term['name'], term['description'], term['uri'], term['source'])

        