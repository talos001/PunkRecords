import click
from pathlib import Path
from .config import load_config
from .vaults.material_vault import MaterialVault
from .vaults.index_vault import IndexVault
from .agent import AgentRegistry
from .agent.claude_code import ClaudeCodeAgent
from .agent.codex import CodexAgent
from .agent.opencode import OpenCodeAgent


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def cli(ctx, config):
    """PunkRecords - A thinking second brain for your knowledge."""
    if config:
        ctx.obj = load_config(Path(config))


@cli.command()
@click.option("--domain", "-d", required=True, help="Domain to ingest into")
@click.argument("path")
@click.pass_context
def ingest(ctx, domain, path):
    """Ingest a note into the knowledge base."""
    config = ctx.obj
    material_path = config.materials_vault_path / path
    # TODO: Full implementation
    click.echo(f"Ingesting {material_path} into domain {domain}...")


@cli.command()
@click.argument("question")
@click.pass_context
def query(ctx, question):
    """Query the knowledge base with a question."""
    # TODO: Full implementation
    click.echo(f"Query: {question}")


@cli.command()
@click.pass_context
def lint(ctx):
    """Lint and reorganize the knowledge base."""
    # TODO: Full implementation
    click.echo("Linting knowledge base...")


@cli.command("serve")
@click.option("--host", default="127.0.0.1", help="监听地址")
@click.option("--port", default=8765, type=int, help="监听端口")
@click.option("--reload", is_flag=True, help="开发模式自动重载")
def serve_cmd(host: str, port: int, reload: bool):
    """启动 HTTP API（FastAPI + Uvicorn）。"""
    import uvicorn

    uvicorn.run(
        "punkrecords.api.app:app",
        host=host,
        port=port,
        reload=reload,
    )


def main():
    """Main entry point."""
    # Register all agents
    registry = AgentRegistry()
    registry.register(ClaudeCodeAgent)
    registry.register(CodexAgent)
    registry.register(OpenCodeAgent)

    cli()


if __name__ == "__main__":
    main()
