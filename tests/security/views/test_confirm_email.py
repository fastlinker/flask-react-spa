import pytest

from flask import url_for
from flask_security import current_user, AnonymousUser
from flask_security_bundle import SecurityService, UserManager


@pytest.mark.options(SECURITY_CONFIRMABLE=True)
class TestConfirmEmail:
    def register(self, user_manager: UserManager, security_service: SecurityService):
        user = user_manager.create(username='test',
                                   email='test@example.com',
                                   password='password',
                                   first_name='the',
                                   last_name='user')
        security_service.register_user(user)
        return user

    def test_confirm_email(self, client, registrations, confirmations,
                           user_manager: UserManager,
                           security_service: SecurityService):
        user = self.register(user_manager, security_service)
        assert len(registrations) == 1
        assert user == registrations[0]['user']
        assert not user.active
        assert not user.confirmed_at

        confirm_token = registrations[0]['confirm_token']
        r = client.get('security.confirm_email', token=confirm_token)
        assert r.status_code == 302
        assert r.path == url_for('frontend.index')
        assert r.query == 'welcome'

        assert len(confirmations) == 1
        assert user in confirmations

        assert user.active
        assert user.confirmed_at
        assert current_user == user

    @pytest.mark.options(SECURITY_CONFIRM_EMAIL_WITHIN='-1 seconds')
    def test_expired_token(self, client, registrations, confirmations, outbox,
                           templates,
                           user_manager: UserManager,
                           security_service: SecurityService):
        user = self.register(user_manager, security_service)
        assert len(registrations) == 1

        confirm_token = registrations[0]['confirm_token']
        r = client.get('security.confirm_email', token=confirm_token)
        assert r.status_code == 302
        assert r.path == url_for('frontend.resend_confirmation_email')

        assert len(confirmations) == 0
        assert len(outbox) == len(templates) == 2
        assert templates[0].template.name == 'security/email/welcome.html'
        assert templates[1].template.name == 'security/email/confirmation_instructions.html'
        assert templates[1].context.get('confirmation_link')

        assert not user.active
        assert not user.confirmed_at
        assert isinstance(current_user._get_current_object(), AnonymousUser)

    def test_invalid_token(self, client, registrations, confirmations, outbox,
                           templates,
                           user_manager: UserManager,
                           security_service: SecurityService):
        user = self.register(user_manager, security_service)
        assert len(registrations) == 1

        r = client.get('security.confirm_email', token='fail')
        assert r.status_code == 302
        assert r.path == url_for('frontend.resend_confirmation_email')

        assert len(confirmations) == 0
        assert len(outbox) == len(templates) == 1
        assert templates[0].template.name == 'security/email/welcome.html'

        assert not user.active
        assert not user.confirmed_at
        assert isinstance(current_user._get_current_object(), AnonymousUser)
