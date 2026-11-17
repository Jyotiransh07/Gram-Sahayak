import argparse
from app.rag import ingest

if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='Index trusted PDF/TXT/MD documents for Gram Sahayak.')
    parser.add_argument('--vectors', action='store_true', help='Also build multilingual semantic Chroma index')
    args = parser.parse_args()
    print(ingest(replace=True, use_vectors=args.vectors))
