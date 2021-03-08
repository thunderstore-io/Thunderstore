from typing import List

import click
from click import BadParameter

from loadtest.loadtest import start_loadtest


@click.command()
@click.option("--clients", default=30, help="Number of simultaneous clients", type=int)
@click.option(
    "--host", default="http://localhost", help="The host to test against", type=str
)
@click.option(
    "--paths", default=["/"], help="The paths to loadtest", type=str, multiple=True
)
@click.option(
    "--limit", default=5000, help="Total number of requests to send", type=int
)
@click.option(
    "--no-limit",
    default=False,
    help="Keep running forever",
    type=bool,
    is_flag=True,
)
@click.option(
    "--log-interval",
    default=50,
    help="How many requests should be between each log output",
    type=int,
)
def execute_from_command_line(
    clients: int,
    host: str,
    paths: List[str],
    limit: int,
    no_limit: bool,
    log_interval: int,
):
    if not paths:
        raise BadParameter("At least a single path must be defined", param="paths")
    if no_limit:
        limit = None
    start_loadtest(
        clients=clients,
        host=host,
        paths=paths,
        limit=limit,
        log_interval=log_interval,
    )
