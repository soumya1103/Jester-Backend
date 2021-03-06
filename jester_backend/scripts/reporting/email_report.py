from __future__ import division
from datetime import timedelta
import django
import numpy as np
import operator
import os

__author__ = 'Viraj Mahesh'

# Setup code required before importing modules
os.environ['DJANGO_SETTINGS_MODULE'] = 'jester_backend.settings'
django.setup()

from jester.models import *
from django.core.mail import send_mail

MAX_TOP_RATED_JOKES = 10
MAX_TOP_VARIANCE_JOKES = 10

TOP_RATED_JOKE_TMPL = 'Joke {0}. Mean Rating: {1:.3f}'
TOP_VARIANCE_JOKE_TMPL = 'Joke {0}. Variance: {1:.3f}'

SETTINGS = {
    'to': ['virajmahesh@berkeley.edu', 'goldberg@berkeley.edu',
           'sanjaykrishn@gmail.com', 'patel.jay@berkeley.edu'],
    'from': 'jester@rieff.ieor.berkeley.edu',
    'subject': 'Jester v5 Daily Report'
}


def merge_dictionaries(*args):
    result = {}
    for dictionary in args:
        result.update(dictionary)
    return result


def populate(rating_matrix, rating):
    rating_matrix[rating.user_id - 1][rating.joke_id - 1] = rating.to_float()


def main():
    report = file('report.tmpl')
    template = report.read()
    report.close()

    time = timezone.now().time()
    today = timezone.now().date()
    yesterday = today + timedelta(days=-1)

    daily_ratings = Rating.objects.filter(timestamp__range=[yesterday, today])

    users = Rater.objects.count()
    jokes = Joke.objects.count()
    all_ratings = Rating.objects.count()

    rating_matrix = np.zeros((users, jokes))
    rating_matrix.fill(np.nan)

    daily_rating_matrix = np.zeros((users, jokes))
    daily_rating_matrix.fill(np.nan)

    for rating in Rating.objects.all():
        populate(rating_matrix, rating)

    for rating in daily_ratings:
        populate(daily_rating_matrix, rating)

    rating_count = np.array([user.jokes_rated for user in Rater.objects.all()])

    header = {
        'time': time.strftime('%H:%M:%S'),
        'today': today.strftime('%m/%d/%y'),
        'yesterday': today.strftime('%m/%d/%y')
    }

    daily_stats = {
        'daily_ratings_count': daily_ratings.count(),
        'mean_daily_rating': np.nanmean(daily_rating_matrix),
        'median_daily_rating': np.nanmedian(daily_rating_matrix),
    }

    aggregate_stats = {
        'total_users': users,
        'total_ratings': all_ratings,
        'mean_rating': np.nanmean(rating_matrix),
        'median_rating': np.nanmedian(rating_matrix),
        'min_rating': np.nanmin(rating_matrix),
        'max_rating': np.nanmax(rating_matrix),
        'mean_number_of_jokes_rated': np.nanmean(rating_count),
        'median_number_of_jokes_rated': np.nanmedian(rating_count),
        'min_number_of_jokes_rated': np.nanmin(rating_count),
        'max_number_of_jokes_rated': np.nanmax(rating_count)
    }

    mean_ratings = np.nanmean(rating_matrix, axis=0)
    mean_ratings = [(id + 1, mean) for id, mean in enumerate(mean_ratings)]
    mean_ratings.sort(key=operator.itemgetter(1), reverse=True)

    variances = np.nanvar(rating_matrix, axis=0)
    variances = [(id + 1, variance) for id, variance in enumerate(variances)]
    variances.sort(key=operator.itemgetter(1), reverse=True)

    for i in xrange(MAX_TOP_RATED_JOKES):
        id, mean = mean_ratings[i]
        joke = 'top_rated_joke_{0}'.format(i + 1)
        aggregate_stats[joke] = TOP_RATED_JOKE_TMPL.format(id, mean)

    for i in xrange(MAX_TOP_VARIANCE_JOKES):
        id, variance = variances[i]
        joke = 'top_variance_joke_{0}'.format(i + 1)
        aggregate_stats[joke] = TOP_VARIANCE_JOKE_TMPL.format(id, variance)

    report_parameters = merge_dictionaries(header, daily_stats, aggregate_stats)
    report = template.format(**report_parameters)

    send_mail(SETTINGS['subject'], report, SETTINGS['from'], SETTINGS['to'])


if __name__ == '__main__':
    main()
