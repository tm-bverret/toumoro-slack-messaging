from os import environ
from re import compile as comp
from copy import copy
from pprint import pformat
from typing import List, Optional, Union, Dict, Tuple
from urllib.parse import quote_plus

from requests import post, RequestException, Response
from colorama import init, deinit, Fore, Style


def post_message(
    url: str,
    headers: Dict[str, str],
    body: Dict[str, Union[List[Dict[str, str]], Optional[str]]],
) -> str:
    response: Response = post.request(url=url, headers=headers, json=body)
    response.raise_for_status()
    timestamp: str = response.json()['message']['ts']
    print(f"::set-output name=timestamp::{timestamp}")
    return timestamp


def build_status_element(status_string: str) -> List[Dict[str, str]]:
    status_list: List[Dict[str, str]] = []
    regex = comp(r"(?(DEFINE)(?<status>\w*:(?:FAIL|PASS)))^(?&status)(?:;(?&status))*$")
    assert bool(
        regex.match(str(status_string))
    ), f"Invalid status string {status_string}, must fit (?(DEFINE)(?<status>\\w*:(?:FAIL|PASS)))^(?&status)(?:;(?&status))*$"
    for status in status_string.split(";"):
        name: str
        state: str
        name, state = status.split(":")
        status_list.append({"name": name, "status": state})
    return status_list


def github_message_builder(
    url_call: str, status: List[Dict[str, str]]
) -> Tuple[str, Dict[str, str], Dict[str, Union[List[Dict[str, str]], Optional[str]]]]:
    body: Dict[str, Union[List[Dict[str, str]], Optional[str]]] = {
        "status": status,
        "issue_id": environ.get("ISSUE_ID", None),
        "github_actor": environ["ACTOR"],
        "github_repository": environ.get("REPOSITORY", None),
        "workflow": environ.get("WORKFLOW", None),
        "slack_timestamp": environ.get("TIMESTAMP", None),
    }

    headers: Dict[str, str] = {
        "Content-Type": "application/json",
        "X-API-Key": environ["API_KEY"],
    }
    return url_call, headers, body


def main() -> str:
    base_url: str = environ["API_URL"]
    if not base_url.startswith("http"):
        base_url = f"https://{base_url}"
    if not base_url.endswith("/"):
        base_url = f"{base_url}/"
    service: str = environ["SERVICE"]
    assert service in [
        "github",
        "gitlab",
        "bitbucket",
    ], "Service must be either 'github', 'gitlab' or 'bitbucket'"
    channel: str = quote_plus(environ["CHANNEL"])
    project: str = quote_plus(environ["PROJECT"])
    ref: str = quote_plus(environ["REF"])
    run_id: str = quote_plus(environ["RUN_ID"])
    step: str = quote_plus(environ["STEP"])
    type_message: str = quote_plus(environ["TYPE"])

    url_call: str = f"{base_url}{service}/{channel}/{project}/{ref}/{run_id}/{step}/{type_message}/"

    status: List[Dict[str, str]] = build_status_element(environ["STATUS"])

    url: str = ""
    headers: Dict[str, str] = {}
    body: Dict[str, Union[List[Dict[str, str]], Optional[str]]] = {}

    if service == "github":
        url, headers, body = github_message_builder(url_call, status)
    elif service == "gitlab":
        # url, headers, body = gitlab_message_builder(url_call, status)
        pass
    elif service == "bitbucket":
        # url, headers, body = bitbucket_message_builder(url_call, status)
        pass

    verbose: int = int(environ.get("VERBOSE", 0))

    print(f"{Fore.BLUE}Call to URL: {Fore.WHITE}{url}")
    if verbose == 1:
        print(f"{Fore.BLUE}With parameters:")
        print(f"{Fore.WHITE}{pformat(body, indent=4)}")
    if verbose == 2:
        print(f"{Fore.BLUE}With headers:")
        safe_header: Dict[str, str] = copy(headers)
        safe_header["X-API-Key"] = f"{safe_header['X-API-Key'][0:4]}..."
        print(f"{Fore.WHITE}{pformat(safe_header, indent=4)}")
    return post_message(url, headers, body)


if __name__ == "__main__":
    init(autoreset=True)
    try:
        print(f"{Fore.BLUE}{Style.BRIGHT}Toumoro Slack Messaging")
        timestamp: str = main()
    except AssertionError as err:
        print(f"{Fore.RED}{err}")
        exit(42)
    except RequestException as err:
        print(f"{Fore.RED}Error either from the API or the request")
        exit(42)
    except KeyError as err:
        print(f"{Fore.RED}Missing parameters")
        exit(42)
    else:
        print(f"{Fore.GREEN}Request successful with message timestamp '{Fore.WHITE}{Style.BRIGHT}{timestamp}'")
    finally:
        deinit()
