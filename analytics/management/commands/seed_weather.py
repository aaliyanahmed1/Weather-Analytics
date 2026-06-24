import os
import pandas as pd
from django.core.management.base import BaseCommand
from analytics.models import WeatherRecord

class Command(BaseCommand):
    help = 'Seeds the database with sample weather records from weather_sample.csv'

    def handle(self, *args, **options):
        csv_path = os.path.join(os.path.dirname(os.path.dirname(os.path.dirname(os.path.dirname(__file__)))), 'weather_sample.csv')
        
        if not os.path.exists(csv_path):
            self.stdout.write(self.style.ERROR(f"Could not find sample CSV file at {csv_path}"))
            return
            
        self.stdout.write(self.style.SUCCESS(f"Reading sample CSV file from {csv_path}"))
        
        try:
            df = pd.read_csv(csv_path)
            df.columns = df.columns.str.lower()
            
            created_count = 0
            for _, row in df.iterrows():
                parsed_date = pd.to_datetime(row['date']).date()
                
                # Check / Create record
                record, created = WeatherRecord.objects.update_or_create(
                    date=parsed_date,
                    defaults={
                        'temperature': float(row['temperature']),
                        'humidity': float(row['humidity']),
                        'wind_speed': float(row['wind_speed']),
                        'precipitation': float(row['precipitation']),
                        'condition': str(row['condition']).strip().capitalize()
                    }
                )
                if created:
                    created_count += 1
                    
            self.stdout.write(self.style.SUCCESS(f"Successfully seeded database with {created_count} weather records!"))
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Error seeding database: {str(e)}"))
