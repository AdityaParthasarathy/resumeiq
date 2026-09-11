def register_blueprints(app):
    from app.routes.main import main_bp
    from app.routes.upload import upload_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
