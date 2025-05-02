import sqlite3
from django.core.management.base import BaseCommand
from games.models import Team, DimDate, TeamDatePoint


class Command(BaseCommand):
    help = 'Populates the TeamDatePoint model with data calculated from games'

    def handle(self, *args, **options):
        self.stdout.write('Starting to populate TeamDatePoint table...')
        
        # Clear existing data
        self.stdout.write('Clearing existing TeamDatePoint data...')
        TeamDatePoint.objects.all().delete()
        
        # Calculate day of season for each date
        self.stdout.write('Calculating day of season for each date...')
        seasons = DimDate.objects.values_list('season', flat=True).distinct()
        
        for season in seasons:
            if not season:
                continue
                
            # Get all dates for this season in chronological order
            dates = DimDate.objects.filter(season=season).order_by('date')
            
            # Calculate day of season for regular season and playoffs separately
            for phase in ['regular', 'post']:  # Using the phase names from dim_date.py
                phase_dates = dates.filter(season_phase=phase)
                
                for i, date_obj in enumerate(phase_dates):
                    # Update day_of_season (1-based)
                    date_obj.day_of_season = i + 1
                    date_obj.save()
                    
                    self.stdout.write(f'  Set {date_obj} ({season}, {phase}) as day {date_obj.day_of_season}')
        
        # Calculate team points for each date
        self.stdout.write('Calculating team points for each date...')
        
        # Connect to the SQLite database directly for games data
        conn = sqlite3.connect('games.db')
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        
        teams = Team.objects.all()
        dates = DimDate.objects.all().order_by('date')
        
        for team in teams:
            self.stdout.write(f'Processing team: {team}')
            
            # Initialize counters
            season_stats = {}
            
            for date_obj in dates:
                # Skip if date is empty
                if not date_obj.date:
                    continue
                    
                current_date = date_obj.date.date().strftime('%Y-%m-%d')
                current_season = date_obj.season
                
                # If we're at a new season, reset the counters
                if current_season not in season_stats:
                    season_stats[current_season] = {
                        'wins': 0,
                        'loses': 0,
                        'otl': 0,  # Overtime loss
                        'sol': 0,  # Shootout loss
                    }
                
                # Get all games for this team up to and including this date in this season
                # Need to join with dim_date to filter by season
                cursor.execute('''
                    SELECT g.* 
                    FROM games g
                    INNER JOIN dim_date dd ON g.game_date = dd.date
                    WHERE dd.season = ? 
                    AND DATE(g.game_date) <= DATE(?)
                    AND (g.home_team = ? OR g.away_team = ?)
                    AND g.game_status LIKE 'Final%'
                    ORDER BY g.game_date
                ''', (current_season, current_date, team.name, team.name))
                
                games = cursor.fetchall()
                
                # Reset counters for this date
                wins = 0
                loses = 0
                otl = 0
                sol = 0
                
                # Process each game
                for game in games:
                    is_home = game['home_team'] == team.name
                    home_score = game['home_team_score']
                    away_score = game['away_team_score']
                    game_status = game['game_status']
                    
                    # Check if team won
                    if ((is_home and home_score > away_score) or 
                        (not is_home and away_score > home_score)):
                        wins += 1
                    # Check if team lost in regulation
                    elif ((is_home and home_score < away_score and game_status == 'Final') or 
                          (not is_home and away_score < home_score and game_status == 'Final')):
                        loses += 1
                    # Check if team lost in overtime
                    elif ((is_home and home_score < away_score and game_status == 'Final OT') or 
                          (not is_home and away_score < home_score and game_status == 'Final OT')):
                        otl += 1
                    # Check if team lost in shootout
                    elif ((is_home and home_score < away_score and game_status == 'Final SO') or 
                          (not is_home and away_score < home_score and game_status == 'Final SO')):
                        sol += 1
                
                # Calculate total points (2 for win, 1 for OT/SO loss)
                total_points = (wins * 2) + otl + sol
                
                # Create TeamDatePoint record
                TeamDatePoint.objects.create(
                    team=team,
                    date=date_obj,
                    wins=wins,
                    loses=loses,
                    otl=otl,
                    sol=sol,
                    total_points=total_points
                )
                
                self.stdout.write(f'  {date_obj} - {team}: {wins}W, {loses}L, {otl}OTL, {sol}SOL = {total_points} points')
        
        # Close the database connection
        conn.close()
        
        self.stdout.write(self.style.SUCCESS('Successfully populated TeamDatePoint table!'))