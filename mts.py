import argparse
import csv
import json
import shutil
import subprocess
import sys
import time
from datetime import datetime, timezone
from pathlib import Path


def read_location() -> dict[str, object]:
	result = subprocess.run(
		["termux-location", "-p", "gps", "-r", "once"],
		check=True,
		capture_output=True,
		text=True,
		timeout=60,
	)
	location = json.loads(result.stdout)
	if "latitude" not in location or "longitude" not in location:
		raise ValueError(f"Location response did not include coordinates: {location}")
	return location


def main() -> int:
	parser = argparse.ArgumentParser(
		description="Log this Android phone's GPS location locally using Termux:API."
	)
	parser.add_argument(
		"--interval",
		type=float,
		default=30,
		help="Seconds between readings (default: 30)",
	)
	parser.add_argument(
		"--output",
		type=Path,
		default=Path("locations.csv"),
		help="CSV output path (default: locations.csv)",
	)
	args = parser.parse_args()

	if args.interval <= 0:
		parser.error("--interval must be greater than zero")
	if sys.platform != "linux":
		print(
			"This GPS logger must run inside Termux on the Android phone. "
			"Copy mts.py to the phone, install Termux:API and the termux-api "
			"package there, then run it from Termux.",
			file=sys.stderr,
		)
		return 1
	if shutil.which("termux-location") is None:
		print(
			"termux-location is missing. Install the Termux:API Android app, "
			"then run `pkg install termux-api` in Termux.",
			file=sys.stderr,
		)
		return 1

	columns = [
		"timestamp_utc",
		"latitude",
		"longitude",
		"altitude",
		"accuracy",
		"speed",
		"bearing",
		"provider",
	]
	needs_header = not args.output.exists() or args.output.stat().st_size == 0

	print(f"Logging this device's location to {args.output}. Press Ctrl+C to stop.")
	try:
		with args.output.open("a", newline="", encoding="utf-8") as file:
			writer = csv.DictWriter(file, fieldnames=columns, extrasaction="ignore")
			if needs_header:
				writer.writeheader()
			while True:
				location = read_location()
				row = {
					"timestamp_utc": datetime.now(timezone.utc).isoformat(),
					**location,
				}
				writer.writerow(row)
				file.flush()
				print(
					f"{row['timestamp_utc']}  "
					f"{location['latitude']}, {location['longitude']}"
				)
				time.sleep(args.interval)
	except KeyboardInterrupt:
		print("\nStopped.")
	except (OSError, subprocess.SubprocessError, json.JSONDecodeError, ValueError) as error:
		print(f"Could not read location: {error}", file=sys.stderr)
		return 1
	return 0


if __name__ == "__main__":
	raise SystemExit(main())
