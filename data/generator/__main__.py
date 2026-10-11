"""CLI entrypoint for synthetic receipt generation: python -m data.generator."""

import argparse
from pathlib import Path

from data.generator.generator import generate_receipts


def main() -> None:
    parser = argparse.ArgumentParser(description="Kharcha Synthetic Receipt Generator")
    parser.add_argument(
        "--n",
        type=int,
        default=200,
        help="Number of synthetic receipts to generate (default: 200)",
    )
    parser.add_argument(
        "--out",
        type=str,
        default="data/generated",
        help="Output directory (default: data/generated)",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed for reproducible generation (default: 42)",
    )
    args = parser.parse_args()

    out_dir = Path(args.out)
    print(f"Generating {args.n} receipts into {out_dir} (seed={args.seed})...")
    generate_receipts(n=args.n, output_dir=out_dir, seed=args.seed)
    print(f"Done! Created {args.n} receipts and labels at {out_dir / 'labels.csv'}")


if __name__ == "__main__":
    main()
