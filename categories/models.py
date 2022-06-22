from django.db import models
from django.contrib.auth.models import User
from django.forms import ModelForm

import datetime, random, hashlib

class Version(models.Model):
    '''
    A translation of Proverbs (NIV, NASB, etc).
    '''
    short_name = models.CharField(max_length=20)
    full_name = models.CharField(max_length=200)
    publisher_name = models.CharField(max_length=200)
    permission_to_quote = models.TextField(
        help_text='Usually on the copyright page.')
    copyright = models.TextField()

    def __unicode__(self):
        return self.full_name

    class Meta:
        ordering = ('full_name',)

class VersionForm(ModelForm):
    class Meta:
        model = Version

class Reference(models.Model):
    '''
    A reference for a verse from Proverbs (the chapter and verse).

    Example:
    3:1
    '''
    chapter = models.IntegerField()
    verse = models.IntegerField()

    def __unicode__(self):
        return "%d:%d" % (self.chapter, self.verse)

    class Meta:
        ordering = ('chapter', 'verse',)

class ReferenceForm(ModelForm):
    class Meta:
        model = Reference

class Verse(models.Model):
    '''
    A verse from Proverbs (it's reference and associated scripture and the
    name of the version used).
    '''
    reference = models.ForeignKey('Reference', related_name='script_reference')
    scripture = models.TextField()
    version = models.ForeignKey('Version')

    def __unicode__(self):
        return "%s (%s)" % (self.reference,
                self.version.full_name)

    class Meta:
        ordering = ('version', 'reference',)

class VerseForm(ModelForm):
    class Meta:
        model = Verse

class Passage(models.Model):
    '''
    A set of verses that are related.
    '''

    references = models.ManyToManyField('Reference')
    version = models.ForeignKey('Version')

    def get_min_max_verse(self):
        verses = self.references.values()
        if not verses:
            return (0, 0, 0, 0)
        min_verse = verses[0]['verse']
        min_chapter = verses[0]['chapter']

        max_verse = verses[0]['verse']
        max_chapter = verses[0]['chapter']

        for verse in verses:
            this_chapter, this_verse = verse['chapter'], verse['verse']

            if min_chapter > this_chapter:
                min_chapter = this_chapter
                min_verse = this_verse
            elif min_chapter == this_chapter:
                if min_verse > this_verse:
                    min_verse = this_verse

            if max_chapter < this_chapter:
                max_chapter = this_chapter
                max_verse = this_verse
            elif max_chapter == this_chapter:
                if max_verse < this_verse:
                    max_verse = this_verse

        return (min_chapter, min_verse, max_chapter, max_verse)

    def get_reference(self):
        """
        Print the reference to the scripture.
        """
        return self.__unicode__()

    def get_scripture(self):
        """
        Print the scripture related to the passage.
        """
        scripture_text = ""
        for reference in self.references.all():
            scripture_text += Verse.objects.get(reference=reference,
                            version=self.version).scripture

        return scripture_text

    def __unicode__(self):

        (min_chapter, min_verse, max_chapter, max_verse) =  \
                self.get_min_max_verse()

        if (min_chapter, min_verse) == (max_chapter, max_verse):
            return "%d:%d" % (min_chapter, min_verse)
        else:
            if min_chapter == max_chapter:
                return "%d:%d - %d" % (min_chapter, min_verse, max_verse)
            else:
                return "%d:%d - %d:%d" % (min_chapter,
                        min_verse,
                        max_chapter,
                        max_verse)

class PassageForm(ModelForm):
    class Meta:
        model = Passage




#
# This looks promising now:
# https://django-registration.readthedocs.io/en/2.4.1/hmac.html
#


def get_new_key(user):
    """
    Return a tuple of an activation key and the expiration date
    for the same.
    """
    salt = hashlib.sha256(str(random.random())).hexdigest()[:5]
    activation_key = hashlib.sha256(
            salt + user.username).hexdigest()[:40]
    key_expires = datetime.datetime.today() + datetime.timedelta(2)

    return activation_key, key_expires

class UserProfile(models.Model):
    '''
    Define the session information stored for each user.
    '''

    user = models.ForeignKey(User, unique=True)
    default_version = models.ForeignKey('Version')

    # For registration.
    activation_key = models.CharField(max_length=40)
    key_expires = models.DateTimeField()

    def __unicode__(self):
        return self.user.username

    def get_or_create_profile(user):
        """
        Given the user, return the profile if it exists or create a new one.
        """

        try:
            profile = UserProfile.objects.get(user=user)
        except UserProfile.DoesNotExist:
            version = Version.objects.get(
                    full_name="New International Version - 1984")

            activation_key, key_expires = get_new_key(user)

            profile = UserProfile.objects.get_or_create(user=user,
                    default_version=version,
                    show_references=True,
                    activation_key=activation_key,
                    key_expires=key_expires)

        return profile

    # With this, just reference <user>.profile in a view and the profile will be
    # created.
    User.profile = property(get_or_create_profile)
