from django.db import models

class DailyStat(models.Model):
    date = models.DateField(unique=True, db_index=True)
    total_leads = models.IntegerField(default=0)
    new_leads = models.IntegerField(default=0)
    closed_won = models.IntegerField(default=0)
    closed_lost = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    avg_deal_size = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    conversion_rate = models.FloatField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Kunlik Statistika'
        verbose_name_plural = 'Kunlik Statistikalar'
        ordering = ['-date']

    def __str__(self):
        return f"{self.date}: {self.new_leads} yangi, {self.total_revenue:,.0f} so'm"

class WeeklyReport(models.Model):
    week_start = models.DateField()
    week_end = models.DateField()
    report_text = models.TextField()
    stats_data = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Haftalik Hisobot'
        verbose_name_plural = 'Haftalik Hisobotlar'
        ordering = ['-week_start']

    def __str__(self):
        return f"Hisobot: {self.week_start} — {self.week_end}"

class ManagerStat(models.Model):
    date = models.DateField(db_index=True)
    manager_id = models.IntegerField()
    manager_name = models.CharField(max_length=255)
    leads_count = models.IntegerField(default=0)
    won_count = models.IntegerField(default=0)
    lost_count = models.IntegerField(default=0)
    revenue = models.DecimalField(max_digits=15, decimal_places=2, default=0)
    conversion_rate = models.FloatField(default=0)

    class Meta:
        verbose_name = 'Menejer Statistikasi'
        verbose_name_plural = 'Menejer Statistikalari'
        ordering = ['-date', '-revenue']
        unique_together = ['date', 'manager_id']

    def __str__(self):
        return f"{self.manager_name} — {self.date}"
