import re

from django.core.exceptions import ValidationError
from django.http import HttpRequest, HttpResponse
from django.utils.translation import ugettext as _

from zerver.decorator import require_realm_admin
from zerver.lib.actions import do_add_realm_playground, do_remove_realm_playground
from zerver.lib.request import REQ, JsonableError, has_request_variables
from zerver.lib.response import json_error, json_success
from zerver.lib.validator import check_capped_string, check_url
from zerver.models import Realm, RealmPlayground, UserProfile


def check_pygments_language(var_name: str, val: object) -> str:
    s = check_capped_string(RealmPlayground.MAX_PYGMENTS_LANGUAGE_LENGTH)(var_name, val)
    # We don't want to restrict the language here to be only from the list of valid
    # Pygments languages. Keeping it open would allow us to hook up a "playground"
    # for custom "languages" that aren't known to Pygments. We use a similar strategy
    # even in our fenced_code markdown processor.
    valid_pygments_language = re.compile(r"^[ a-zA-Z0-9_+-./#]*$")
    matched_results = valid_pygments_language.match(s)
    if not matched_results:
        raise JsonableError(_("Invalid characters in pygments language"))
    return s


def access_playground_by_id(realm: Realm, playground_id: int) -> RealmPlayground:
    try:
        realm_playground = RealmPlayground.objects.get(id=playground_id, realm=realm)
    except RealmPlayground.DoesNotExist:
        raise JsonableError(_("Invalid playground"))
    return realm_playground


@require_realm_admin
@has_request_variables
def add_realm_playground(
    request: HttpRequest,
    user_profile: UserProfile,
    name: str = REQ(),
    url_prefix: str = REQ(validator=check_url),
    pygments_language: str = REQ(validator=check_pygments_language),
) -> HttpResponse:
    try:
        playground_id = do_add_realm_playground(
            realm=user_profile.realm,
            name=name.strip(),
            pygments_language=pygments_language.strip(),
            url_prefix=url_prefix.strip(),
        )
    except ValidationError as e:
        return json_error(e.messages[0], data={"errors": dict(e)})
    return json_success({"id": playground_id})


@require_realm_admin
@has_request_variables
def delete_realm_playground(
    request: HttpRequest, user_profile: UserProfile, playground_id: int
) -> HttpResponse:
    realm_playground = access_playground_by_id(user_profile.realm, playground_id)
    do_remove_realm_playground(user_profile.realm, realm_playground)
    return json_success()
