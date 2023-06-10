from datetime import date
import random

import faker

fake = faker.Faker()

game_date = date(2023, 5, 13).strftime('%A, %b  %d, %Y')
game_attendance = format(6212,',')
home_score = str(random.randint(0,9))
home_team = f'{fake.first_name()} {fake.last_name()}'
away_score = str(random.randint(0,9))
away_team = f'{fake.first_name()} {fake.last_name()}'
game_status = fake.word()

RESPONSE_TEXT = [
    f'{away_team} {away_score} at {home_team} {home_score} - Status: {game_status}',
    f'{game_date} - Coca-Cola Coliseum',
    'Rochester 1 4 2 - 7',
    'Toronto 0 2 2 - 4',
    '1st Period-1, Rochester, Kulich 5 (Jobst, Prow), 9:57 (PP). Penalties-Shaw Tor (tripping), 8:00; Clifford Tor (roughing), 15:09; Bartkowski Roc (tripping), 17:30; Jobst Roc (cross-checking), 20:00.',
    '2nd Period-2, Toronto, Abruzzese 2 (Hollowell, Shaw), 1:20 (PP). 3, Rochester, Davies 1 (Malone, Pilut), 4:28. 4, Rochester, Rousek 1 (Jobst), 5:58. 5, Rochester, Malone 2 (Cecconi, Warren), 7:01. 6, Rochester, Cecconi 1 (Cederqvist, Mersch), 7:13. 7, Toronto, Ellis 1 (Niemelä, Zohorna), 10:08 (PP). Penalties-Hoefenmayer Tor (cross-checking), 2:25; Bartkowski Roc (hooking), 8:19; Jobst Roc (roughing), 16:01.',
    '3rd Period-8, Toronto, Holmberg 3 (Abruzzese, Hollowell), 5:03 (PP). 9, Rochester, Mersch 5 (Malone, Rosen), 7:12 (PP). 10, Rochester, Warren 1 (Murray, Jobst), 16:15 (EN). 11, Toronto, Steeves 1 (Ellis, Zohorna), 18:22 (PP). Penalties-Chyzowski Tor (interference), 2:14; served by Eliot Roc (bench minor - too many men), 4:43; Blandisi Tor (high-sticking), 5:43; Eliot Roc (boarding), 16:43.',
    'Shots on Goal-Rochester 8-14-9-31. Toronto 9-20-9-38.',
    'Power Play Opportunities-Rochester 2 / 5; Toronto 4 / 6.',
    'Goalies-Rochester, Subban 7-4 (38 shots-34 saves). Toronto, Källgren 2-1 (19 shots-15 saves); Petruzzelli 1-2 (11 shots-9 saves).',
    f'A-{game_attendance}',
    'Referees-Cody Beach (45), Beau Halkidis (48).',
    'Linesmen-Ryan Jackson (84), Joseph Mahon (89).'
]

RESPONSE_NOT_YET_AVAILABLE_TEXT = ['This game is not available.']

RESPONSE_GAME_NOT_PLAYED_TEXT = ['{"error": "No such game"}']

RESPONSE = f'<html>\n\n<head>\n    <title>Official statistics powered by LeagueStat.com</title>\n    <META http-equiv="Content-Type" content="text/html; charset=UTF-8">\n</head>\n\n<body>\n\n    <br clear="all">\n    {away_team} {away_score} at {home_team} {home_score} - Status: {game_status}<br />{game_date} - Coca-Cola Coliseum<br /><br />Rochester 1 4 2 - 7<br />Toronto 0 2 2 - 4<br /><br />1st Period-1, Rochester, Kulich 5 (Jobst, Prow), 9:57 (PP). Penalties-Shaw Tor (tripping), 8:00; Clifford Tor (roughing), 15:09; Bartkowski Roc (tripping), 17:30; Jobst Roc (cross-checking), 20:00.<br /><br />2nd Period-2, Toronto, Abruzzese 2 (Hollowell, Shaw), 1:20 (PP). 3, Rochester, Davies 1 (Malone, Pilut), 4:28. 4, Rochester, Rousek 1 (Jobst), 5:58. 5, Rochester, Malone 2 (Cecconi, Warren), 7:01. 6, Rochester, Cecconi 1 (Cederqvist, Mersch), 7:13. 7, Toronto, Ellis 1 (Niemelä, Zohorna), 10:08 (PP). Penalties-Hoefenmayer Tor (cross-checking), 2:25; Bartkowski Roc (hooking), 8:19; Jobst Roc (roughing), 16:01.<br /><br />3rd Period-8, Toronto, Holmberg 3 (Abruzzese, Hollowell), 5:03 (PP). 9, Rochester, Mersch 5 (Malone, Rosen), 7:12 (PP). 10, Rochester, Warren 1 (Murray, Jobst), 16:15 (EN). 11, Toronto, Steeves 1 (Ellis, Zohorna), 18:22 (PP). Penalties-Chyzowski Tor (interference), 2:14; served by Eliot Roc (bench minor - too many men), 4:43; Blandisi Tor (high-sticking), 5:43; Eliot Roc (boarding), 16:43.<br /><br />Shots on Goal-Rochester 8-14-9-31. Toronto 9-20-9-38.<br />Power Play Opportunities-Rochester 2 / 5; Toronto 4 / 6.<br />Goalies-Rochester, Subban 7-4 (38 shots-34 saves). Toronto, Källgren 2-1 (19 shots-15 saves); Petruzzelli 1-2 (11 shots-9 saves).<br />A-{game_attendance}<br />Referees-Cody Beach (45), Beau Halkidis (48).<br />Linesmen-Ryan Jackson (84), Joseph Mahon (89).\n</body>\n\n</html>'

RESPONSE_GAME_NOT_PLAYED = '<html>\n\n<head>\n    <title>Official statistics powered by LeagueStat.com</title>\n    <META http-equiv="Content-Type" content="text/html; charset=UTF-8">\n</head>\n\n<body>\n\n    <br clear="all">\n    {"error": "No such game"}'

RESPONSE_NOT_YET_AVAILABLE = '<html>\n\n<head>\n    <title>Official statistics powered by LeagueStat.com</title>\n    <META http-equiv="Content-Type" content="text/html; charset=UTF-8">\n</head>\n\n<body>\n\n    <br clear="all">\n    This game is not available.\n</body>\n\n</html>' 