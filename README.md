# AHL Scraper

A small script to scrape the AHL site to get details about games played

## Set Up

Create a virtual environment and then pip install the `requirements.txt` file

## Tests

Run `pytest`

## Helpful links

[Average Home Attandance for each team in 2023-24](https://ahl-data.vercel.app/games?sql=select+home_team%0D%0A%2C+sum%28game_attendance%29%0D%0A%2C+avg%28game_attendance%29%0D%0A%2C+count%28game_attendance%29%0D%0Afrom+games+%0D%0Awhere+game_date+%3E%3D+%272023-10-13%27%0D%0Agroup+by+home_team%0D%0Aorder+by+avg%28game_attendance%29+desc%0D%0A)

[Details on Games played in 2023-24](https://ahl-data.vercel.app/games?sql=select+sum%28home_team_score%29%0D%0A%2C+sum%28game_attendance%29%0D%0A%2C+avg%28game_attendance%29%0D%0A%2C+count%28*%29%0D%0A%2C+%27Home%27+as+%27Location%27%0D%0Afrom+games+%0D%0Awhere+game_date+%3E%3D+%272023-10-13%27%0D%0Aand+home_team+%3D+%27Coachella+Valley+Firebirds%27%0D%0Aunion+all%0D%0Aselect+sum%28away_team_score%29%0D%0A%2C+sum%28game_attendance%29%0D%0A%2C+avg%28game_attendance%29%0D%0A%2C+count%28*%29%0D%0A%2C+%27Away%27%0D%0Afrom+games+%0D%0Awhere+game_date+%3E%3D+%272023-10-13%27%0D%0Aand+away_team+%3D+%27Coachella+Valley+Firebirds%27%0D%0A%0D%0A%0D%0A)