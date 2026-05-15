import sys
from app.api.server import create_app


def main():
    app = create_app()
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 5000
    print(f"Starting Auto Backtest API on port {port}...")
    app.run(host="0.0.0.0", port=port, debug=True)


if __name__ == "__main__":
    main()
