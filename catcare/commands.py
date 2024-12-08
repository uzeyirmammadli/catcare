import click
from flask.cli import with_appcontext
import json
from datetime import datetime
import logging
from flask import current_app
import inspect

logging.basicConfig(level=logging.INFO)

@click.command('dumpdata')
@click.argument('filename', required=False, type=click.Path())
@with_appcontext
def dump_data_command(filename=None):
    """Export all data from database to JSON."""
    from . import models
    from .models import db
    
    # Get all models defined in models.py
    model_classes = []
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and issubclass(obj, db.Model) and obj != db.Model:
            model_classes.append(obj)
    
    # Dump data for each model
    data = {}
    for model in model_classes:
        try:
            table_name = model.__tablename__
            instances = model.query.all()
            data[table_name] = [
                {c.name: getattr(instance, c.name) 
                 for c in instance.__table__.columns}
                for instance in instances
            ]
            click.echo(f"Exported {len(instances)} records from {table_name}")
            
        except Exception as e:
            click.echo(f"Error exporting {table_name}: {e}", err=True)
    
    # Write to file or stdout
    json_data = json.dumps(data, default=str, indent=2)
    if filename:
        with open(filename, 'w') as f:
            f.write(json_data)
        click.echo(f"Data written to {filename}")
    else:
        print(json_data)

@click.command('loaddata')
@click.argument('filename', type=click.Path(exists=True))
@with_appcontext
def load_data_command(filename):
    """Import data from JSON file into database."""
    from . import models
    from .models import db

    # Get all models
    model_classes = {}
    for name, obj in inspect.getmembers(models):
        if inspect.isclass(obj) and issubclass(obj, db.Model) and obj != db.Model:
            model_classes[obj.__tablename__] = obj

    # Read JSON file
    with open(filename, 'r') as f:
        data = json.load(f)

    try:
        # Define the order of tables for deletion and insertion
        # Tables with foreign keys should come first in deletion
        # and last in insertion
        deletion_order = [
            'comment',  # Delete comments first as they depend on cases
            'case',     # Then delete cases
            # Add other tables in appropriate order
        ]

        insertion_order = [
            'case',     # Insert cases first
            'comment',  # Then insert comments that reference cases
            # Add other tables in appropriate order
        ]

        # Delete existing records in correct order
        for table_name in deletion_order:
            if table_name in model_classes:
                Model = model_classes[table_name]
                Model.query.delete()
                click.echo(f"Deleted existing records from {table_name}")

        db.session.commit()

        # Insert new records in correct order
        for table_name in insertion_order:
            if table_name not in data:
                continue
                
            if table_name not in model_classes:
                click.echo(f"Warning: No model found for table {table_name}")
                continue

            Model = model_classes[table_name]
            records = data[table_name]

            for record in records:
                instance = Model(**record)
                db.session.add(instance)

            click.echo(f"Loaded {len(records)} records into {table_name}")
            db.session.commit()  # Commit after each table to ensure references exist

        click.echo("Data loaded successfully")

    except Exception as e:
        db.session.rollback()
        click.echo(f"Error loading data: {e}", err=True)
        raise
def register_commands(app):
    """Register CLI commands with Flask app."""
    app.cli.add_command(dump_data_command)
    app.cli.add_command(load_data_command)  # Add this line
