"""Start the CampusShield portal.

Examples
  python scripts/run_app.py                         # secure build on 127.0.0.1:5000
  python scripts/run_app.py --mode vulnerable --port 5001
  python scripts/run_app.py --host 0.0.0.0 --tls    # HTTPS with a self-signed lab certificate

The vulnerable build refuses to listen on anything except loopback unless
--allow-lab-exposure is given (only used inside the isolated Kali lab script).
"""
import argparse
import ipaddress
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from app.web import create_app  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description="CampusShield portal")
    ap.add_argument("--mode", choices=["secure", "vulnerable"], default="secure")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=5000)
    ap.add_argument("--tls", action="store_true", help="serve HTTPS with a self-signed certificate")
    ap.add_argument("--cert", default=None, help="certificate file (PEM) for --tls")
    ap.add_argument("--key", default=None, help="private key file (PEM) for --tls")
    ap.add_argument("--allow-lab-exposure", action="store_true",
                    help="allow the vulnerable build on a non-loopback address (isolated lab only)")
    args = ap.parse_args()

    if args.mode == "vulnerable" and not args.allow_lab_exposure:
        try:
            loopback = ipaddress.ip_address(args.host).is_loopback
        except ValueError:
            loopback = args.host == "localhost"
        if not loopback:
            sys.exit("Refusing: the vulnerable build may only bind to loopback outside the isolated lab.")

    ssl_ctx = None
    if args.tls:
        ssl_ctx = (args.cert, args.key) if args.cert and args.key else "adhoc"

    app = create_app(args.mode)
    print(f"CampusShield ({args.mode}) on {'https' if args.tls else 'http'}://{args.host}:{args.port}")
    app.run(host=args.host, port=args.port, debug=False, ssl_context=ssl_ctx)


if __name__ == "__main__":
    main()
