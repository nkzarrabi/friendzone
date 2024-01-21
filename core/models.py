from django.conf import settings
from django.db import models, transaction
import django.contrib.auth.models as auth_models

MAX_CONNECTIONS_PER_USER = 50

class ConnectionLimitException(Exception):
    pass

class User(auth_models.AbstractUser):
    name = models.CharField(max_length=256)

    def save(self, **kwargs):
        create_default_circles = self.pk is None

        result = super().save(**kwargs)

        if create_default_circles:
            for name in ['Friends', 'Family']:
                circle = Circle(owner=self, name=name)
                circle.save()

        return result

    @property
    def connections(self):
        return Connection.objects.filter(
            inviting_user=self,
        ).union(
            Connection.objects.filter(
                accepting_user=self,
            ),
        )

    @transaction.atomic
    def create_invitation(self, *, circles):
        circles_count = circles.count()

        if circles_count == 0:
            raise Exception('Invitation must have at least one circle')

        if circles_count != circles.filter(owner=self).count():
            raise Exception('Cannot invite to circle you do not own')

        if self.connections.count() >= MAX_CONNECTIONS_PER_USER:
            raise ConnectionLimitException('Connection limit reached')

        invitation = Invitation.objects.create(owner=self)

        invitation.circles.set(circles)
        return invitation

    @transaction.atomic
    def accept_invitation(self, invitation, *, circles):
        circles_count = circles.count()

        if circles_count == 0:
            raise Exception('Must accept into at least one circle')

        if circles_count != circles.filter(owner=self).count():
            raise Exception('Cannot cannot accept into circle you do not own')

        connection = Connection.objects.create(
            inviting_user=invitation.owner,
            accepting_user=self,
        )

        for circle in invitation.circles.all():
            connection.circles.add(circle)
        for circle in circles.all():
            connection.circles.add(circle)

        connection.save()

class Invitation(models.Model):
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='invitations'
    )
    circles = models.ManyToManyField(
        'Circle',
        related_name='+',
    )

class ConnectionManager(models.Manager):
    @transaction.atomic
    def create(self, **kwargs):
        inviting_user = kwargs.get('inviting_user')
        if inviting_user.connections.count() >= MAX_CONNECTIONS_PER_USER:
            raise ConnectionLimitException(
                'Inviting user has reached connection limit',
            )

        accepting_user = kwargs.get('accepting_user')
        if accepting_user.connections.count() >= MAX_CONNECTIONS_PER_USER:
            raise ConnectionLimitException(
                'Accepting user has reached connection limit',
            )

        return super().create(**kwargs)

class Connection(models.Model):
    objects = ConnectionManager()

    created_utc = models.DateTimeField(auto_now_add=True)
    inviting_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='+'
    )
    accepting_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='+'
    )
    circles = models.ManyToManyField(
        'Circle',
        related_name='connections',
    )

class Circle(models.Model):
    name = models.CharField(max_length=64)
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='circles'
    )

    @property
    def members(self):
        return User.objects.filter(
            pk__in=self.connections.filter(
                accepting_user=self.owner,
            ).values_list(
                'inviting_user',
                flat=True,
            ).union(
                self.connections.filter(
                    inviting_user=self.owner,
                ).values_list(
                    'accepting_user',
                    flat=True,
                )
            )
        )

class Message(models.Model):
    connection = models.ForeignKey(
        'Connection',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    from_user = models.ForeignKey(
        'User',
        on_delete=models.CASCADE,
        related_name='messages',
    )
    created_utc = models.DateTimeField(auto_now_add=True)
    read = models.BooleanField(default=False)
    text = models.CharField(max_length=1024)

class Post(models.Model):
    circle = models.ForeignKey(
        'Circle',
        on_delete=models.CASCADE,
        related_name='posts',
    )
    created_utc = models.DateTimeField(auto_now_add=True)
    text = models.CharField(max_length=1024)