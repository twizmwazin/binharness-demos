from __future__ import annotations

import logging
import os
from pathlib import Path

import binharness
from binharness import InjectableExecutor, Target, Process, export_target, import_target
from binharness.bootstrap.docker import bootstrap_env_from_image

logging.basicConfig(
    level=logging.WARNING, format="%(levelname)7s | %(name)30s | %(message)s"
)
logging.getLogger("bh_agent_client.bindings").setLevel(logging.DEBUG)
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)

OUTPUT_FILE = "/tmp/strace.out"


class TrivialStrace(InjectableExecutor):
    def __init__(self):
        super().__init__(
            Path(os.path.join(os.path.dirname(__file__), "trivial-strace"))
        )

    def _run_target(self: TrivialStrace, target: Target) -> Process:
        self.proc = target.environment.run_command(
            self.env_path,
            "-o",
            OUTPUT_FILE,
            "--",
            target.main_binary,
            *target.args,
            env=target.env,
        )
        return self.proc

    def collect_results(self):
        self.proc.wait()
        logger.info("stdout:")
        logger.info(self.proc.stdout.read())
        with self.environment.open_file(OUTPUT_FILE, "r") as f:
            logger.info("strace:")
            for line in f.read().split(b"\n"):
                logger.info(line)


logger.info("Bootstrapping container...")
agent_conn = bootstrap_env_from_image(
    # os.path.join(os.path.dirname(__file__), "bh_agent_server"),
    "/Users/kevin/workspace/binharness/target/aarch64-unknown-linux-musl/debug/bh_agent_server",
    "ubuntu:22.04",
    agent_log="DEBUG",
)

local_env = binharness.LocalEnvironment()
logger.info("Getting remote environment...")
remote_env = agent_conn.get_environment(0)

local_target = Target(
    main_binary=Path("demo.bin"),
    args=[],
    env={},
    environment=local_env,
)
logger.info("Exporting target...")
export_target(local_target, Path(__file__).parent / "demo.bht")
logger.info("Importing target...")
remote_target = import_target(remote_env, Path(__file__).parent / "demo.bht")

executor = TrivialStrace()
logger.info("Installing executor...")
executor.install(remote_env)
logger.info("Running target...")
executor.run_target(remote_target)
logger.info("Collecting results...")
executor.collect_results()
