# AHL Scraper

A small script to scrape the AHL site to get details about games played. It runs on a schedule and posts the games.db to a vercel project. 

The project leverages the great library [datasette](https://datasette.io/)


## Helpful links

[Average Home Attandance for each team in 2023-24](https://ahl-data.ryancheley.com/games?sql=select+home_team%0D%0A%2C+sum%28game_attendance%29%0D%0A%2C+avg%28game_attendance%29%0D%0A%2C+count%28game_attendance%29%0D%0Afrom+games+%0D%0Awhere+game_date+%3E%3D+%272023-10-13%27%0D%0Agroup+by+home_team%0D%0Aorder+by+avg%28game_attendance%29+desc%0D%0A)

[Details on Games played in 2023-24](https://ahl-data.ryancheley.com/games?sql=select+sum%28home_team_score%29+as+%27Total+Goals%27%0D%0A%2C+sum%28game_attendance%29+as+%27Total+Home+Team+Attendance%27%0D%0A%2C+Round%28avg%28game_attendance%29%2C+0%29+as+%27Average+Home+Team+Attendance%27%0D%0A%2C+count%28*%29+as+%27Games+Player%27%0D%0A%2C+round%28sum%28home_team_score%29+*+1.0+%2F+count%28*%29%2C+2%29+as+%27Average+Goals+Per+Game%27%0D%0A%2C+%27Home%27+as+%27Location%27%0D%0Afrom+games+g%0D%0Ainner+join+dim_date+dd+on+g.game_date+%3D+dd.date%0D%0Awhere+dd.season+%3D+%3Aseason%0D%0Aand+home_team+%3D+%3Ateam%0D%0Aunion+all%0D%0Aselect+sum%28away_team_score%29%0D%0A%2C+sum%28game_attendance%29%0D%0A%2C+avg%28game_attendance%29%0D%0A%2C+count%28*%29%0D%0A%2C+round%28sum%28away_team_score%29+*+1.0+%2F+count%28*%29%2C2%29+as+%27Average+Goals+Per+Game%27%0D%0A%2C+%27Away%27%0D%0Afrom+games+g%0D%0Ainner+join+dim_date+dd+on+g.game_date+%3D+dd.date%0D%0Awhere+dd.season+%3D+%3Aseason%0D%0Aand+away_team+%3D+%3Ateam%0D%0A%0D%0A%0D%0A&team=Coachella+Valley+Firebirds&season=2023-24)
