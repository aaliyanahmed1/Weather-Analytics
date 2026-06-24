import io
import datetime
import urllib.request
import urllib.parse
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login, logout, authenticate
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.contrib import messages
from django.http import HttpResponse, JsonResponse
from django.db.models import Avg, Max, Min, Count
from django.db import IntegrityError
import pandas as pd
import numpy as np

# ReportLab imports for PDF generation
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib import colors

from .models import WeatherRecord, Profile
from .forms import SignUpForm, UserUpdateForm, ProfileUpdateForm, WeatherRecordForm

# ----------------- User Auth & Profile Views -----------------

def signup_view(request):
    if request.user.is_authenticated:
        return redirect('dashboard')
    if request.method == 'POST':
        form = SignUpForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Registration successful! Welcome to the Weather Analytics Portal.")
            return redirect('dashboard')
        else:
            messages.error(request, "Registration failed. Please correct the errors below.")
    else:
        form = SignUpForm()
    return render(request, 'analytics/signup.html', {'form': form})

@login_required
def profile_view(request):
    if request.method == 'POST':
        u_form = UserUpdateForm(request.POST, instance=request.user)
        p_form = ProfileUpdateForm(request.POST, instance=request.user.profile)
        if u_form.is_valid() and p_form.is_valid():
            u_form.save()
            p_form.save()
            messages.success(request, "Your profile has been updated successfully!")
            return redirect('profile')
        else:
            messages.error(request, "Failed to update profile. Please check the inputs.")
    else:
        u_form = UserUpdateForm(instance=request.user)
        p_form = ProfileUpdateForm(instance=request.user.profile)
    
    return render(request, 'analytics/profile.html', {
        'u_form': u_form,
        'p_form': p_form
    })

# ----------------- Dashboard & Analytics Views -----------------

@login_required
def dashboard_view(request):
    records = WeatherRecord.objects.all()
    
    # Filter handling
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    condition = request.GET.get('condition')
    
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    if condition:
        records = records.filter(condition=condition)
        
    count = records.count()
    
    # Aggregated Summary Stats (using Django ORM or Pandas if we want)
    stats = {
        'count': count,
        'avg_temp': 0.0,
        'max_temp': 0.0,
        'min_temp': 0.0,
        'avg_humidity': 0.0,
        'max_wind': 0.0,
        'total_precip': 0.0
    }
    
    insights = []
    
    if count > 0:
        agg = records.aggregate(
            avg_temp=Avg('temperature'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            avg_humidity=Avg('humidity'),
            max_wind=Max('wind_speed'),
            total_precip=Avg('precipitation') # using average precipitation or sum
        )
        stats['avg_temp'] = round(agg['avg_temp'] or 0.0, 1)
        stats['max_temp'] = round(agg['max_temp'] or 0.0, 1)
        stats['min_temp'] = round(agg['min_temp'] or 0.0, 1)
        stats['avg_humidity'] = round(agg['avg_humidity'] or 0.0, 1)
        stats['max_wind'] = round(agg['max_wind'] or 0.0, 1)
        stats['total_precip'] = round(agg['total_precip'] or 0.0, 1)
        
        # Load data to Pandas for complex insights
        vals = list(records.values('date', 'temperature', 'humidity', 'wind_speed', 'precipitation', 'condition'))
        df = pd.DataFrame(vals)
        df['date'] = pd.to_datetime(df['date'])
        
        # 1. Hottest Month
        df['month_year'] = df['date'].dt.to_period('M')
        monthly_avg = df.groupby('month_year')['temperature'].mean()
        if not monthly_avg.empty:
            hottest_month = monthly_avg.idxmax()
            hottest_val = round(monthly_avg.max(), 1)
            insights.append(f"🔥 The hottest month on record is <strong>{hottest_month}</strong> with an average temperature of <strong>{hottest_val}°C</strong>.")
            
        # 2. Extreme Weather Trends
        heatwave_days = df[df['temperature'] >= 35].shape[0]
        stormy_days = df[df['condition'] == 'Stormy'].shape[0]
        heavy_rain_days = df[df['precipitation'] >= 25].shape[0]
        
        if heatwave_days > 0:
            insights.append(f"☀️ Detected <strong>{heatwave_days}</strong> heatwave days (temp &ge; 35°C), suggesting intense summer patterns.")
        if stormy_days > 0:
            insights.append(f"⚡ Detected <strong>{stormy_days}</strong> stormy days, representing periods of high atmospheric instability.")
        if heavy_rain_days > 0:
            insights.append(f"🌧️ Detected <strong>{heavy_rain_days}</strong> days of heavy precipitation (&ge; 25mm), highlighting potential flood risks.")
            
        # 3. Correlation Insight (NumPy)
        if len(df) > 1:
            corr = np.corrcoef(df['temperature'], df['humidity'])[0, 1]
            if not np.isnan(corr):
                corr_str = "negative" if corr < 0 else "positive"
                strength = "strong" if abs(corr) > 0.6 else "moderate" if abs(corr) > 0.3 else "weak"
                insights.append(f"📊 Statistically, there is a <strong>{strength} {corr_str} correlation</strong> ({round(corr, 2)}) between Temperature and Humidity.")

    # Unique conditions for filters
    conditions = WeatherRecord.CONDITION_CHOICES
    
    return render(request, 'analytics/dashboard.html', {
        'stats': stats,
        'insights': insights,
        'conditions': conditions,
        'records_count': count,
        'start_date': start_date or '',
        'end_date': end_date or '',
        'selected_condition': condition or ''
    })

@login_required
def dashboard_chart_data(request):
    """Endpoint for supplying chart data in JSON format"""
    records = WeatherRecord.objects.all().order_by('date')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    condition = request.GET.get('condition')
    
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    if condition:
        records = records.filter(condition=condition)
        
    vals = list(records.values('date', 'temperature', 'humidity', 'wind_speed', 'precipitation', 'condition'))
    if not vals:
        return JsonResponse({
            'dates': [], 'temps': [], 'humidity': [], 'wind': [], 'precip': [], 'conditions': {}, 'cond_counts': []
        })
        
    df = pd.DataFrame(vals)
    df['date'] = df['date'].apply(lambda x: x.strftime('%Y-%m-%d'))
    
    # Condition distribution
    cond_counts = df['condition'].value_counts().to_dict()
    
    return JsonResponse({
        'dates': df['date'].tolist(),
        'temps': df['temperature'].tolist(),
        'humidity': df['humidity'].tolist(),
        'wind': df['wind_speed'].tolist(),
        'precip': df['precipitation'].tolist(),
        'cond_labels': list(cond_counts.keys()),
        'cond_values': list(cond_counts.values())
    })

# ----------------- Weather Record CRUD Views -----------------

@login_required
def record_list_view(request):
    records = WeatherRecord.objects.all().order_by('-date')
    return render(request, 'analytics/record_list.html', {'records': records})

@login_required
def record_create_view(request):
    if request.method == 'POST':
        form = WeatherRecordForm(request.POST)
        if form.is_valid():
            try:
                form.save()
                messages.success(request, "Weather record added successfully!")
                return redirect('record_list')
            except IntegrityError:
                messages.error(request, "A record for this date already exists.")
        else:
            messages.error(request, "Failed to create record. Please correct form errors.")
    else:
        form = WeatherRecordForm()
    return render(request, 'analytics/record_form.html', {'form': form, 'title': 'Add Weather Record'})

@login_required
def record_update_view(request, pk):
    record = get_object_or_404(WeatherRecord, pk=pk)
    if request.method == 'POST':
        form = WeatherRecordForm(request.POST, instance=record)
        if form.is_valid():
            form.save()
            messages.success(request, "Weather record updated successfully!")
            return redirect('record_list')
        else:
            messages.error(request, "Failed to update record. Please verify inputs.")
    else:
        form = WeatherRecordForm(instance=record)
    return render(request, 'analytics/record_form.html', {'form': form, 'title': 'Edit Weather Record'})

@login_required
def record_delete_view(request, pk):
    record = get_object_or_404(WeatherRecord, pk=pk)
    if request.method == 'POST':
        record.delete()
        messages.success(request, "Weather record deleted successfully.")
        return redirect('record_list')
    return render(request, 'analytics/record_confirm_delete.html', {'record': record})

# ----------------- CSV Import View -----------------

@login_required
def upload_csv_view(request):
    if request.method == 'POST':
        csv_file = request.FILES.get('file')
        if not csv_file or not csv_file.name.endswith('.csv'):
            messages.error(request, "Please upload a valid CSV file.")
            return redirect('upload_csv')
            
        try:
            # Read CSV using Pandas
            df = pd.read_csv(csv_file)
            
            # Column mapping check
            required_cols = {'date', 'temperature', 'humidity', 'wind_speed', 'precipitation', 'condition'}
            if not required_cols.issubset(df.columns.str.lower()):
                messages.error(request, f"CSV must contain these headers: {', '.join(required_cols)}")
                return redirect('upload_csv')
            
            # Normalize column names to lowercase
            df.columns = df.columns.str.lower()
            
            # Cleaning: drop rows with missing essential fields, fill others
            df = df.dropna(subset=['date', 'temperature', 'condition'])
            df['humidity'] = df['humidity'].fillna(50.0)
            df['wind_speed'] = df['wind_speed'].fillna(0.0)
            df['precipitation'] = df['precipitation'].fillna(0.0)
            
            success_count = 0
            error_count = 0
            
            for _, row in df.iterrows():
                try:
                    # Parse date format robustly
                    parsed_date = pd.to_datetime(row['date']).date()
                    
                    # Create or update weather record
                    WeatherRecord.objects.update_or_create(
                        date=parsed_date,
                        defaults={
                            'temperature': float(row['temperature']),
                            'humidity': float(row['humidity']),
                            'wind_speed': float(row['wind_speed']),
                            'precipitation': float(row['precipitation']),
                            'condition': str(row['condition']).strip().capitalize()
                        }
                    )
                    success_count += 1
                except Exception:
                    error_count += 1
            
            if success_count > 0:
                messages.success(request, f"Successfully processed CSV. Added/Updated {success_count} records.")
            if error_count > 0:
                messages.warning(request, f"Failed to process {error_count} records due to formatting/integrity issues.")
                
            return redirect('dashboard')
        except Exception as e:
            messages.error(request, f"Error processing file: {str(e)}")
            return redirect('upload_csv')
            
    return render(request, 'analytics/upload_csv.html')

# ----------------- Exports -----------------

@login_required
def export_csv_view(request):
    records = WeatherRecord.objects.all().order_by('date')
    
    # Filter handling to match dashboard filtered state
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    condition = request.GET.get('condition')
    
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    if condition:
        records = records.filter(condition=condition)

    response = HttpResponse(content_type='text/csv')
    response['Content-Disposition'] = f'attachment; filename="weather_data_{datetime.date.today()}.csv"'
    
    # Let Pandas build the CSV output buffer
    vals = list(records.values('date', 'temperature', 'humidity', 'wind_speed', 'precipitation', 'condition'))
    if vals:
        df = pd.DataFrame(vals)
        df.to_csv(path_or_buf=response, index=False)
    else:
        df = pd.DataFrame(columns=['date', 'temperature', 'humidity', 'wind_speed', 'precipitation', 'condition'])
        df.to_csv(path_or_buf=response, index=False)
        
    return response

@login_required
def export_pdf_view(request):
    records = WeatherRecord.objects.all().order_by('date')
    
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    condition = request.GET.get('condition')
    
    if start_date:
        records = records.filter(date__gte=start_date)
    if end_date:
        records = records.filter(date__lte=end_date)
    if condition:
        records = records.filter(condition=condition)

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="weather_summary_{datetime.date.today()}.pdf"'

    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=letter, rightMargin=40, leftMargin=40, topMargin=40, bottomMargin=40)
    story = []

    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'DocTitle',
        parent=styles['Heading1'],
        fontName='Helvetica-Bold',
        fontSize=24,
        textColor=colors.HexColor('#1e293b'),
        spaceAfter=15
    )
    subtitle_style = ParagraphStyle(
        'DocSubtitle',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#64748b'),
        spaceAfter=25
    )
    heading_style = ParagraphStyle(
        'SectionHeading',
        parent=styles['Heading2'],
        fontName='Helvetica-Bold',
        fontSize=14,
        textColor=colors.HexColor('#3b82f6'),
        spaceBefore=15,
        spaceAfter=10
    )
    body_style = ParagraphStyle(
        'Body',
        parent=styles['Normal'],
        fontName='Helvetica',
        fontSize=10,
        textColor=colors.HexColor('#334155'),
        spaceAfter=10
    )

    # Document Header
    story.append(Paragraph("Weather Analytics Summary Report", title_style))
    story.append(Paragraph(f"Generated on {datetime.date.today().strftime('%B %d, %Y')} | Prepared by Shakeel Ahmed (F2023065276)", subtitle_style))
    story.append(Spacer(1, 10))

    count = records.count()
    if count > 0:
        agg = records.aggregate(
            avg_temp=Avg('temperature'),
            max_temp=Max('temperature'),
            min_temp=Min('temperature'),
            avg_humidity=Avg('humidity'),
            max_wind=Max('wind_speed'),
            avg_precip=Avg('precipitation')
        )
        
        # Summary Statistics Table
        story.append(Paragraph("Summary Statistics Table", heading_style))
        data = [
            ["Metric", "Value"],
            ["Total Records Checked", str(count)],
            ["Average Temperature", f"{round(agg['avg_temp'] or 0, 1)} °C"],
            ["Maximum Temperature", f"{round(agg['max_temp'] or 0, 1)} °C"],
            ["Minimum Temperature", f"{round(agg['min_temp'] or 0, 1)} °C"],
            ["Average Humidity", f"{round(agg['avg_humidity'] or 0, 1)} %"],
            ["Maximum Wind Speed", f"{round(agg['max_wind'] or 0, 1)} km/h"],
            ["Average Precipitation", f"{round(agg['avg_precip'] or 0, 1)} mm"],
        ]
        
        t = Table(data, colWidths=[200, 200])
        t.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (1, 0), colors.HexColor('#3b82f6')),
            ('TEXTCOLOR', (0, 0), (1, 0), colors.whitesmoke),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (1, 0), 'Helvetica-Bold'),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
            ('TOPPADDING', (0, 0), (-1, -1), 8),
            ('BACKGROUND', (0, 1), (-1, -1), colors.HexColor('#f8fafc')),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor('#e2e8f0')),
        ]))
        story.append(t)
        story.append(Spacer(1, 20))
        
        # Dynamic insights text section
        story.append(Paragraph("Automated Insights Summary", heading_style))
        story.append(Paragraph("The system performed real-time data cleansing and validation using Pandas/NumPy. Key trends found:", body_style))
        
        vals = list(records.values('date', 'temperature', 'humidity', 'wind_speed', 'precipitation', 'condition'))
        df = pd.DataFrame(vals)
        df['date'] = pd.to_datetime(df['date'])
        
        # Hottest month
        df['month_year'] = df['date'].dt.to_period('M')
        monthly_avg = df.groupby('month_year')['temperature'].mean()
        if not monthly_avg.empty:
            hottest_month = monthly_avg.idxmax()
            hottest_val = round(monthly_avg.max(), 1)
            story.append(Paragraph(f"- <b>Hottest Month:</b> {hottest_month} averaged {hottest_val} C.", body_style))
            
        # Extreme events
        heatwave_days = df[df['temperature'] >= 35].shape[0]
        stormy_days = df[df['condition'] == 'Stormy'].shape[0]
        heavy_rain_days = df[df['precipitation'] >= 25].shape[0]
        
        if heatwave_days > 0:
            story.append(Paragraph(f"- <b>Heatwave Danger:</b> {heatwave_days} days registered temperature >= 35 C.", body_style))
        if stormy_days > 0:
            story.append(Paragraph(f"- <b>Storm Warning:</b> {stormy_days} stormy conditions occurred during the period.", body_style))
        if heavy_rain_days > 0:
            story.append(Paragraph(f"- <b>Precipitation Risk:</b> {heavy_rain_days} days had precipitation >= 25mm.", body_style))
            
    else:
        story.append(Paragraph("No records found matching current criteria.", body_style))

    doc.build(story)
    response.write(buffer.getvalue())
    buffer.close()
    return response

def presentation_view(request):
    return render(request, 'analytics/presentation.html')

