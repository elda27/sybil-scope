import sys

from streamlit.web import cli as stcli  # Streamlit 1.32.2〜 の場合


def main():
    sys.argv = [
        "streamlit",
        "run",
        __file__.replace("__main__.py", "app.py"),
    ] + sys.argv[1:]
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
