#!/usr/bin/env python3
"""Calibration harness for `parse_filename` fuzzy threshold.

Produces a CSV of precision/recall/F1 for thresholds and optionally
prints token match debug info for misclassified examples.
"""
import argparse
import csv
from collections import defaultdict
from typing import List

from app.backend.filename_parser import parse_filename


def load_labels(path: str) -> List[dict]:
    rows = []
    with open(path, newline="", encoding="utf-8") as fh:
        r = csv.DictReader(fh)
        for rr in r:
            # expect columns: filename,instrument (instrument can be empty)
            rows.append({"filename": rr.get("filename", "").strip(), "instrument": (rr.get("instrument") or "").strip()})
    return rows


def evaluate(rows, thresholds=range(50, 101), verbose=False):
    results = []
    for thr in thresholds:
        tp = fp = fn = 0
        for r in rows:
            true = r["instrument"] or None
            p = parse_filename(r["filename"], fuzzy_threshold=thr)
            pred = p.get("instrument")
            if pred is not None and true is not None and pred == true:
                tp += 1
            elif pred is not None and (true is None or pred != true):
                fp += 1
            elif pred is None and true is not None:
                fn += 1
        prec = tp / (tp + fp) if (tp + fp) > 0 else 0.0
        rec = tp / (tp + fn) if (tp + fn) > 0 else 0.0
        f1 = 2 * prec * rec / (prec + rec) if (prec + rec) > 0 else 0.0
        results.append({"threshold": thr, "tp": tp, "fp": fp, "fn": fn, "precision": prec, "recall": rec, "f1": f1})
    return results


def write_results(path: str, results):
    with open(path, "w", newline="", encoding="utf-8") as fh:
        w = csv.DictWriter(fh, fieldnames=["threshold", "tp", "fp", "fn", "precision", "recall", "f1"])
        w.writeheader()
        for r in results:
            w.writerow(r)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("labels_csv", nargs="?", default="sandbox/labeled_filenames.csv")
    parser.add_argument("--out", default="sandbox/calibration_results.csv")
    parser.add_argument("--min", type=int, default=50)
    parser.add_argument("--max", type=int, default=100)
    parser.add_argument("--verbose", action="store_true")
    args = parser.parse_args()

    rows = load_labels(args.labels_csv)
    thresholds = range(args.min, args.max + 1)
    results = evaluate(rows, thresholds=thresholds, verbose=args.verbose)
    write_results(args.out, results)
    # print best by f1
    best = max(results, key=lambda r: r["f1"])
    print(f"Best threshold by F1: {best['threshold']} (F1={best['f1']:.3f}, P={best['precision']:.3f}, R={best['recall']:.3f})")
    print(f"Results written to: {args.out}")


if __name__ == "__main__":
    main()
