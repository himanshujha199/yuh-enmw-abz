"""Smoke test: query Qdrant with Hindi text and print results."""
from src.qdrant_client import search_collection, filter_and_search_schemes


def main():
    print("=== Testing Hindi scheme retrieval ===")
    results = filter_and_search_schemes(
        query_text="किसानों के लिए पैसे की मदद",  # "financial help for farmers"
        occupation="farmer",
        land_acres=2.0,
    )
    for r in results:
        print(f"  [{r['score']:.3f}] {r['name']} — {r.get('benefits', '')[:60]}")

    print("\n=== Testing Hindi health retrieval ===")
    results = search_collection("health", "बच्चे को बुखार है दो दिन से")  # "child has fever for 2 days"
    for r in results:
        print(f"  [{r['score']:.3f}] {r['id']} — {r.get('action_mild', '')[:60]}")

    print("\n=== Testing service retrieval ===")
    results = search_collection("services", "ambulance emergency number")
    for r in results:
        print(f"  [{r['score']:.3f}] {r['name']} — {r.get('phone', '')}")

    print("\n=== Testing Hindi service retrieval ===")
    results = search_collection("services", "महिला हेल्पलाइन नंबर")  # "women helpline number"
    for r in results:
        print(f"  [{r['score']:.3f}] {r['name']} — {r.get('phone', '')}")


if __name__ == "__main__":
    main()
