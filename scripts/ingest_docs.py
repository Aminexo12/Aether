import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from app.rag.ingest import ingest_pdf


def main() -> None:
    parser = argparse.ArgumentParser(description="Ingest PDF documents into Qdrant")
    parser.add_argument("--path", required=True, help="Folder containing PDF files")
    parser.add_argument("--collection", default="flight_docs", help="Qdrant collection name")
    args = parser.parse_args()



    

    folder = Path(args.path)
    pdfs = list(folder.glob("*.pdf"))
    if not pdfs:
        print(f"No PDF files found in {folder}")
        return

    total = 0
    for pdf in pdfs:
        print(f"Ingesting {pdf.name}...", end=" ", flush=True)
        t0 = time.time()
        count = ingest_pdf(pdf, collection=args.collection)
        elapsed = time.time() - t0
        print(f"{count} chunks ({elapsed:.1f}s)")
        total += count

    print(f"\nDone. Total chunks ingested: {total}")


if __name__ == "__main__":
    main()
