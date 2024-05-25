class GamesRouter:
    """
    A router to control all database operations on models in the games sqlite database.
    """

    route_app_labels = {
        "games",
    }

    def db_for_read(self, model, **hints):
        """
        Attempts to read games models go to games database.
        """
        if model._meta.app_label == "games":
            return "games"
        return None

    def db_for_write(self, model, **hints):
        """
        Attempts to write games models go to games database.
        """
        if model._meta.app_label == "games":
            return "games"
        return None

    def allow_relation(self, obj1, obj2, **hints):
        """
        Allow relations if a model in the games app is involved.
        """
        if obj1._meta.app_label == "games" or obj2._meta.app_label == "games":
            return True
        return None

    def allow_migrate(self, db, app_label, model_name=None, **hints):
        """
        Make sure the games app only appears in the 'games' database.
        """
        if app_label == "games":
            return db == "games"
        return None
