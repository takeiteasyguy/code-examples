"""
Common logic for APNS push and feedback notifications
"""

from apnsclient import Session, APNs, Message
import datetime
from django.conf import settings
from .models import APNSCredentials
from celery import Task
from .business_logic import get_unread_message_count
OpenSSL.SSL.SSL
import OpenSSLv3_METHOD = OpenSSL.SSL.TLSv1_METHOD


class APNSProvider:

    session = None

    def __init__(self, push_connection=False):
        if not APNSProvider.session:
            APNSProvider.session = Session()
        if settings.DEBUG:
            feedback_property = "feedback_sandbox"
            push_property = "push_sandbox"
        else:
            feedback_property = "feedback_production"
            push_property = "push_production"
        self.connection = APNSProvider.session.new_connection(feedback_property, cert_file=settings.APNS_CERT) \
            if not push_connection else APNSProvider.session.get_connection(push_property,
                                                                            cert_file=settings.APNS_CERT)

    def check_feedback_services_for_tokens(self):
        """
        used only for feedback connection on schedule, remove not available tokens
        """
        services = APNs(self.connection)
        try:
            for token, when in services.feedback():
                last_update = self.get_last_update_of_token(token)
                if last_update and last_update < when:
                    self.remove_token(token)
        except:
            print "Can't connect to APNs, looks like network is down"

    def get_last_update_of_token(self, token):
        try:
            return APNSCredentials.objects.get(token=token).last_update
        except APNSCredentials.DoesNotExist:
            return None

    def remove_token(self, token):
        try:
            APNSCredentials.objects.get(token=token).delete()
        except APNSCredentials.DoesNotExist:
            pass

    def close_outdate_connection(self, delta=5):
        """
        close open unused connections after "delta" time, used on schedule
        """
        delta_time = datetime.timedelta(minutes=delta)
        APNSProvider.session.outdate(delta_time)

    def shutdown_all_connections(self):
        """
        close all connections in pool
        """
        APNSProvider.session.shutdown()

    def send_notification(self, list_tokens, message_title="", message_body="", badge=1):
        """
        push notifications to apns server, used only with push_connection=True
        :param message_body:
        :param message_title:
        :param list_tokens: all tokens to send notifications
        :param badge: number of something new in server
        """
        service = APNs(self.connection)
        try:
            res = service.send(Message(list_tokens, alert={"title": message_title, "body": message_body}, badge=badge))
        except:
            print "Can't connect to APNs, looks like network is down"
        else:
            for token, reason in res.failed.items():
                code, errmsg = reason
                print "Device failed: {0}, reason: {1}".format(token, errmsg)

            for code, errmsg in res.errors:
                print "Error: {}".format(errmsg)

            if res.needs_retry():
                res.retry()



# USAGE EXAMPLE
class MessagePushNotificationTask(Task):
    def run(self, user, message=None):
        # get token if exists
        try:
            token = APNSCredentials.objects.get(user__email=user['email']).token
            # check count of unread messages
            unread_count = get_unread_message_count(user)
            # create push notification session and push new message notification
            if unread_count == 1:
                # in case if there is only one offer unread
                message_title = 'New Message Available'
                message_body = '{from}: {message_text}'.format(from=message.from,
                                                               quantity=message.text)
            else:
                message_title = 'New Messages Available'
                message_body = 'Check new messages!'
            apns_provider = APNSProvider(push_connection=True)
            apns_provider.send_notification([token.replace(" ", "").upper()],
                                            message_title=message_title,
                                            message_body=message_body,
                                            badge=unread_count)
        except APNSCredentials.DoesNotExist:
            pass


def send_message_push_notification_async(**kwargs):
    MessagePushNotificationTask().run(**kwargs)
