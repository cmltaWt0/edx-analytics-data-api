import datetime
from itertools import groupby

from django.db import models
from django.db.models import Case, Count, IntegerField, Max, Sum, When
from django.utils.timezone import now

from analytics_data_api.constants import country, genders
from analytics_data_api.constants.engagement_types import EngagementType
from analytics_data_api.utils import date_range


class BaseCourseModel(models.Model):
    course_id = models.CharField(db_index=True, max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class CourseActivityWeekly(BaseCourseModel):
    """A count of unique users who performed a particular action during a week."""

    class Meta(BaseCourseModel.Meta):
        db_table = 'course_activity'
        index_together = [['course_id', 'activity_type']]
        ordering = ('interval_end', 'interval_start', 'course_id')
        get_latest_by = 'interval_end'

    interval_start = models.DateTimeField()
    interval_end = models.DateTimeField(db_index=True)
    activity_type = models.CharField(db_index=True, max_length=255, db_column='label')
    count = models.IntegerField()

    @classmethod
    def get_most_recent(cls, course_id, activity_type):
        """Activity for the week that was mostly recently computed."""
        return cls.objects.filter(course_id=course_id, activity_type=activity_type).latest('interval_end')


class BaseCourseEnrollment(BaseCourseModel):
    date = models.DateField(null=False, db_index=True)
    count = models.IntegerField(null=False)

    class Meta(BaseCourseModel.Meta):
        abstract = True
        get_latest_by = 'date'
        index_together = [('course_id', 'date',)]


class CourseEnrollmentDaily(BaseCourseEnrollment):
    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_daily'
        ordering = ('date', 'course_id')
        unique_together = [('course_id', 'date',)]


class CourseEnrollmentModeDaily(BaseCourseEnrollment):
    mode = models.CharField(max_length=255)
    cumulative_count = models.IntegerField(null=False)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_mode_daily'
        ordering = ('date', 'course_id', 'mode')
        unique_together = [('course_id', 'date', 'mode')]


class CourseMetaSummaryEnrollment(BaseCourseModel):
    catalog_course_title = models.CharField(db_index=True, max_length=255)
    catalog_course = models.CharField(db_index=True, max_length=255)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField()
    pacing_type = models.CharField(db_index=True, max_length=255)
    availability = models.CharField(db_index=True, max_length=255)
    enrollment_mode = models.CharField(max_length=255)
    count = models.IntegerField(null=False)
    cumulative_count = models.IntegerField(null=False)
    count_change_7_days = models.IntegerField(default=0)
    passing_users = models.IntegerField(default=0)

    class Meta(BaseCourseModel.Meta):
        db_table = 'course_meta_summary_enrollment'
        ordering = ('course_id',)
        unique_together = [('course_id', 'enrollment_mode',)]


class CourseProgramMetadata(BaseCourseModel):
    program_id = models.CharField(db_index=True, max_length=255)
    program_type = models.CharField(db_index=True, max_length=255)
    program_title = models.CharField(max_length=255)

    class Meta(BaseCourseModel.Meta):
        db_table = 'course_program_metadata'
        ordering = ('program_id',)
        unique_together = [('course_id', 'program_id',)]


class CourseEnrollmentByBirthYear(BaseCourseEnrollment):
    birth_year = models.IntegerField(null=False)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_birth_year_daily'
        ordering = ('date', 'course_id', 'birth_year')
        unique_together = [('course_id', 'date', 'birth_year')]


class CourseEnrollmentByEducation(BaseCourseEnrollment):
    education_level = models.CharField(max_length=255, null=True)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_education_level_daily'
        ordering = ('date', 'course_id', 'education_level')
        unique_together = [('course_id', 'date', 'education_level')]


class CourseEnrollmentByGender(BaseCourseEnrollment):
    CLEANED_GENDERS = {
        'f': genders.FEMALE,
        'm': genders.MALE,
        'o': genders.OTHER
    }

    gender = models.CharField(max_length=255, null=True, db_column='gender')

    @property
    def cleaned_gender(self):
        """
        Returns the gender with full names and 'unknown' replacing null/None.
        """
        return self.CLEANED_GENDERS.get(self.gender, genders.UNKNOWN)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_gender_daily'
        ordering = ('date', 'course_id', 'gender')
        unique_together = [('course_id', 'date', 'gender')]


class BaseProblemResponseAnswerDistribution(BaseCourseModel):
    """ Base model for the answer_distribution table. """

    class Meta(BaseCourseModel.Meta):
        db_table = 'answer_distribution'
        abstract = True

    module_id = models.CharField(db_index=True, max_length=255)
    part_id = models.CharField(db_index=True, max_length=255)
    correct = models.NullBooleanField()
    value_id = models.CharField(db_index=True, max_length=255, null=True)
    answer_value = models.TextField(null=True, db_column='answer_value_text')
    variant = models.IntegerField(null=True)
    problem_display_name = models.TextField(null=True)
    question_text = models.TextField(null=True)


class ProblemResponseAnswerDistribution(BaseProblemResponseAnswerDistribution):
    """ Original model for the count of a particular answer to a response to a problem in a course. """

    class Meta(BaseProblemResponseAnswerDistribution.Meta):
        managed = False

    count = models.IntegerField()


class ProblemsAndTags(BaseCourseModel):
    """ Model for the tags_distribution table """

    class Meta(BaseCourseModel.Meta):
        db_table = 'tags_distribution'

    module_id = models.CharField(db_index=True, max_length=255)
    tag_name = models.CharField(max_length=255)
    tag_value = models.CharField(max_length=255)
    total_submissions = models.IntegerField(default=0)
    correct_submissions = models.IntegerField(default=0)


class ProblemFirstLastResponseAnswerDistribution(BaseProblemResponseAnswerDistribution):
    """ Updated model for answer_distribution table with counts of first and last attempts at problems. """

    class Meta(BaseProblemResponseAnswerDistribution.Meta):
        verbose_name = 'first_last_answer_distribution'

    first_response_count = models.IntegerField()
    last_response_count = models.IntegerField()


class CourseEnrollmentByCountry(BaseCourseEnrollment):
    country_code = models.CharField(max_length=255, null=False, db_column='country_code')

    @property
    def country(self):
        """
        Returns a Country object representing the country in this model's country_code.
        """
        return country.get_country(self.country_code)

    class Meta(BaseCourseEnrollment.Meta):
        db_table = 'course_enrollment_location_current'
        ordering = ('date', 'course_id', 'country_code')
        unique_together = [('course_id', 'date', 'country_code')]


class GradeDistribution(BaseCourseModel):
    """ Each row stores the count of a particular grade on a module for a given course. """

    class Meta(BaseCourseModel.Meta):
        db_table = 'grade_distribution'

    module_id = models.CharField(db_index=True, max_length=255)
    grade = models.IntegerField()
    max_grade = models.IntegerField()
    count = models.IntegerField()


class SequentialOpenDistribution(BaseCourseModel):
    """ Each row stores the count of views a particular module has had in a given course. """

    class Meta(BaseCourseModel.Meta):
        db_table = 'sequential_open_distribution'

    module_id = models.CharField(db_index=True, max_length=255)
    count = models.IntegerField()


class BaseVideo(models.Model):
    """ Base video model. """
    pipeline_video_id = models.CharField(db_index=True, max_length=255)
    created = models.DateTimeField(auto_now_add=True)

    class Meta:
        abstract = True


class VideoTimeline(BaseVideo):
    """ Timeline of video segments. """

    segment = models.IntegerField()
    num_users = models.IntegerField()
    num_views = models.IntegerField()

    class Meta(BaseVideo.Meta):
        db_table = 'video_timeline'


class Video(BaseVideo):
    """ Videos associated with a particular course. """

    course_id = models.CharField(db_index=True, max_length=255)
    encoded_module_id = models.CharField(db_index=True, max_length=255)
    duration = models.IntegerField()
    segment_length = models.IntegerField()
    users_at_start = models.IntegerField()
    users_at_end = models.IntegerField()

    class Meta(BaseVideo.Meta):
        db_table = 'video'


class ModuleEngagementTimelineManager(models.Manager):
    """
    Modifies the ModuleEngagement queryset to aggregate engagement data for
    the learner engagement timeline.
    """
    def get_timeline(self, course_id, username):
        queryset = ModuleEngagement.objects.all().filter(course_id=course_id, username=username) \
            .values('date', 'entity_type', 'event') \
            .annotate(total_count=Sum('count')) \
            .annotate(distinct_entity_count=Count('entity_id', distinct=True)) \
            .order_by('date')

        timelines = []

        for date, engagements in groupby(queryset, lambda x: (x['date'])):
            # Iterate over engagements for this day and create a single day with
            # engagement data.
            day = {
                'date': date,
            }
            for engagement in engagements:
                engagement_type = EngagementType(engagement['entity_type'], engagement['event'])

                if engagement_type.is_counted_by_entity:
                    count_delta = engagement['distinct_entity_count']
                else:
                    count_delta = engagement['total_count']

                day[engagement_type.name] = day.get(engagement_type.name, 0) + count_delta
            timelines.append(day)

        # Fill in dates that may be missing, since the result store doesn't
        # store empty engagement entries.
        full_timeline = []
        default_timeline_entry = {engagement_type: 0 for engagement_type in EngagementType.ALL_TYPES}
        for index, current_date in enumerate(timelines):
            full_timeline.append(current_date)
            try:
                next_date = timelines[index + 1]
            except IndexError:
                continue
            one_day = datetime.timedelta(days=1)
            if next_date['date'] > current_date['date'] + one_day:
                full_timeline += [
                    dict(date=date, **default_timeline_entry)
                    for date in date_range(current_date['date'] + one_day, next_date['date'])
                ]

        return full_timeline

    def get_simple_data_for_all_students(self, course_id):
        return ModuleEngagement.objects.all().filter(course_id=course_id) \
            .order_by('username')

    def get_aggregate_engagement_data(self, course_id):
        seven_days_ago = now() - datetime.timedelta(days=7)
        dict_list = [
            ('videos_overall', When(entity_type='video', then='count')),
            ('videos_last_week', When(entity_type='video', created__gt=seven_days_ago, then=1)),
            ('problems_overall', When(entity_type='problem', then='count')),
            ('problems_last_week', When(entity_type='problem', created__gt=seven_days_ago, then='count')),
            ('correct_problems_overall', When(entity_type='problem', event='completed', then='count')),
            ('correct_problems_last_week', When(entity_type='problem', event='completed',
                                                created__gt=seven_days_ago, then='count')),
            ('problems_attempts_overall', When(entity_type='problem', event='attempted', then='count')),
            ('problems_attempts_last_week', When(entity_type='problem', event='attempted',
                                                 created__gt=seven_days_ago, then='count')),
            ('forum_posts_overall', When(entity_type='discussion', then='count')),
            ('forum_posts_last_week', When(entity_type='discussion', created__gt=seven_days_ago, then='count')),
        ]
        dict_parameters = {key: Sum(Case(val, output_field=IntegerField())) for key, val in dict_list}
        dict_parameters['date_last_active'] = Max('created')
        query = ModuleEngagement.objects.filter(course_id=course_id)\
            .values('username')\
            .annotate(**dict_parameters)
        return query


class ModuleEngagement(BaseCourseModel):
    """User interactions with entities within the courseware."""

    username = models.CharField(max_length=255)
    date = models.DateField()
    # This will be one of "problem", "video" or "discussion"
    entity_type = models.CharField(max_length=255)
    # For problems this will be the usage key, for videos it will be the html encoded module ID,
    # for forums it will be the commentable_id
    entity_id = models.CharField(max_length=255)
    # A description of what interaction occurred, e.g. "contributed" or "viewed"
    event = models.CharField(max_length=255)
    # The number of times the user interacted with this entity in this way on this day.
    count = models.IntegerField()

    objects = ModuleEngagementTimelineManager()

    class Meta(BaseCourseModel.Meta):
        db_table = 'module_engagement'


class ModuleEngagementMetricRanges(BaseCourseModel):
    """
    Represents the low and high values for a module engagement entity and event
    pair, known as the metric.  The range_type will either be low, normal, or
    high, bounded by low_value and high_value.
    """

    start_date = models.DateField()
    # This is a left-closed interval. No data from the end_date is included in the analysis.
    end_date = models.DateField()
    metric = models.CharField(max_length=50)
    range_type = models.CharField(max_length=50)
    # Also a left-closed interval, so any metric whose value is equal to the high_value
    # is not included in this range.
    high_value = models.FloatField()
    low_value = models.FloatField()

    class Meta(BaseCourseModel.Meta):
        db_table = 'module_engagement_metric_ranges'
