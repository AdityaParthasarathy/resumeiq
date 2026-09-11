def register_blueprints(app):
    from app.routes.main import main_bp

    app.register_blueprint(main_bp)
