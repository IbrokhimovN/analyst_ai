from rest_framework import serializers
from .models import DailyStat, WeeklyReport, ManagerStat


class DailyStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = DailyStat
        fields = '__all__'


class WeeklyReportSerializer(serializers.ModelSerializer):
    class Meta:
        model = WeeklyReport
        fields = '__all__'


class ManagerStatSerializer(serializers.ModelSerializer):
    class Meta:
        model = ManagerStat
        fields = '__all__'


class SummarySerializer(serializers.Serializer):
    total_leads = serializers.IntegerField()
    new_leads = serializers.IntegerField()
    won_count = serializers.IntegerField()
    lost_count = serializers.IntegerField()
    total_revenue = serializers.FloatField()
    monthly_revenue = serializers.FloatField()
    avg_deal_size = serializers.FloatField()
    conversion_rate = serializers.FloatField()
    period_days = serializers.IntegerField()


class FunnelItemSerializer(serializers.Serializer):
    status_id = serializers.IntegerField()
    status_name = serializers.CharField()
    color = serializers.CharField()
    count = serializers.IntegerField()
    total_value = serializers.FloatField()
