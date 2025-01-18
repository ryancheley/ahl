# Adding a table to the games.db

The Django app that wraps the `games.db` is only meant as a helper to manage the 
data in those tables when neccessary. Because of that any new table(s) added to 
`games.db` need to be added via SQLite and not through the Django `manage.py` 
process that makes migrations and the applies the migrations. 

I did this for a reason, but I'm not sure why.

## An Example

When the table `team_date_point` was added the table had to be created in the 
`games.db` database with this command

```sql
CREATE TABLE "team_date_point" (
	"id"	INTEGER,
	"team_id"	INTEGER,
	"date"	INTEGER,
	"wins"	INTEGER,
	"loses"	INTEGER,
	"otl"	INTEGER,
	"sol"	INTEGER,
	"total_points"	INTEGER,
	UNIQUE("team_id","date"),
	PRIMARY KEY("id" AUTOINCREMENT)
);
```

When creating the table you'll want to ensure that the `id` field is there. There
are ways to make it so that's **not** required, but honestly it's just easier
this way.

Once the table was in the `games.db` database then I [added a new model](https://github.com/ryancheley/ahl/blob/0bc92782a6f24eba9d02c9ebcb844c9077fe0a48/games/models.py#L98)

and [added the model to the admin](https://github.com/ryancheley/ahl/blob/0bc92782a6f24eba9d02c9ebcb844c9077fe0a48/games/admin.py#L25)

I might look at making table additions easier using the Django process in the 
future, but honesly, given the number of times tables will need to be added,
I'm not sure it's worth it