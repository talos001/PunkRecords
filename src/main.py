import click
from pathlib import Path

from .agent import AgentRegistry
from .agent.claude_code import ClaudeCodeAgent
from .agent.codex import CodexAgent
from .agent.opencode import OpenCodeAgent
from .config import load_config


def _cli_config(ctx: click.Context):
    """``--config``、当前目录 ``config.yaml`` 或报错。"""
    if ctx.obj is not None:
        return ctx.obj
    cwd = Path.cwd() / "config.yaml"
    if cwd.is_file():
        return load_config(cwd)
    raise click.UsageError(
        "请使用 --config 指定配置文件，或在当前工作目录放置 config.yaml"
    )


@click.group()
@click.option("--config", "-c", type=click.Path(exists=True), help="Config file path")
@click.pass_context
def cli(ctx, config):
    """PunkRecords - A thinking second brain for your knowledge."""
    if config:
        ctx.obj = load_config(Path(config))


@cli.command()
@click.option("--domain", "-d", required=True, help="领域 id（须与 domain_index_paths 键一致）")
@click.option(
    "--agent",
    "-a",
    default=None,
    help="覆盖 default_agent_backend（如 claude_code）",
)
@click.argument("path", type=str)
@click.pass_context
def ingest(ctx, domain, path, agent):
    """将材料 Vault 内单个文件摄取到该领域的索引 Vault（graph + wiki 元数据）。"""
    from .ingest.service import ingest_material_file

    config = _cli_config(ctx)
    try:
        result = ingest_material_file(
            config, domain, path, agent_backend=agent
        )
    except ValueError as e:
        raise click.ClickException(str(e)) from e
    if not result.success:
        raise click.ClickException(result.error_message or "摄取失败")
    click.echo(
        f"已摄取到领域「{domain}」：实体 {len(result.entities)}，关系 {len(result.relations)}"
    )


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
        "src.api.app:app",
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
