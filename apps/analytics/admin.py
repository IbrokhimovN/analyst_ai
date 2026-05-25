from django.contrib import admin
from .models import DailyStat, WeeklyReport, ManagerStat

@admin.register(DailyStat)
class DailyStatAdmin(admin.ModelAdmin):
    list_display = ['date', 'total_leads', 'new_leads', 'closed_won', 'closed_lost', 'total_revenue']
    list_filter = ['date']
    ordering = ['-date']

@admin.register(WeeklyReport)
class WeeklyReportAdmin(admin.ModelAdmin):
    list_display = ['week_start', 'week_end', 'created_at']
    ordering = ['-week_start']

@admin.register(ManagerStat)
class ManagerStatAdmin(admin.ModelAdmin):
    list_display = ['manager_name', 'date', 'leads_count', 'won_count', 'revenue', 'conversion_rate']
    list_filter = ['date', 'manager_name']
    ordering = ['-date', '-revenue']
