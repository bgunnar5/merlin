import click


@click.command()
@click.option(
    "--task_server",
    required=False,
    default="celery",
    type=click.Choice(["celery"], case_sensitive=False),
    help="Task server type.",
)
def cli(task_server):
    """
    Remove all tasks from all merlin queues (default).
    If a user would like to purge only selected queues use:
    --steps to give a steplist, the queues will be defined from the step list
    """
    print(f"task server = {task_server}.")
