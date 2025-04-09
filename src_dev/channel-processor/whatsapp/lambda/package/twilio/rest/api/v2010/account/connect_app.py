r"""
    This code was generated by
   ___ _ _ _ _ _    _ ____    ____ ____ _    ____ ____ _  _ ____ ____ ____ ___ __   __
    |  | | | | |    | |  | __ |  | |__| | __ | __ |___ |\ | |___ |__/ |__|  | |  | |__/
    |  |_|_| | |___ | |__|    |__| |  | |    |__] |___ | \| |___ |  \ |  |  | |__| |  \

    Twilio - Api
    This is the public Twilio REST API.

    NOTE: This class is auto generated by OpenAPI Generator.
    https://openapi-generator.tech
    Do not edit the class manually.
"""

from typing import Any, Dict, List, Optional, Union, Iterator, AsyncIterator
from twilio.base import serialize, values
from twilio.base.instance_context import InstanceContext
from twilio.base.instance_resource import InstanceResource
from twilio.base.list_resource import ListResource
from twilio.base.version import Version
from twilio.base.page import Page


class ConnectAppInstance(InstanceResource):

    class Permission(object):
        GET_ALL = "get-all"
        POST_ALL = "post-all"

    """
    :ivar account_sid: The SID of the [Account](https://www.twilio.com/docs/iam/api/account) that created the ConnectApp resource.
    :ivar authorize_redirect_url: The URL we redirect the user to after we authenticate the user and obtain authorization to access the Connect App.
    :ivar company_name: The company name set for the Connect App.
    :ivar deauthorize_callback_method: The HTTP method we use to call `deauthorize_callback_url`.
    :ivar deauthorize_callback_url: The URL we call using the `deauthorize_callback_method` to de-authorize the Connect App.
    :ivar description: The description of the Connect App.
    :ivar friendly_name: The string that you assigned to describe the resource.
    :ivar homepage_url: The public URL where users can obtain more information about this Connect App.
    :ivar permissions: The set of permissions that your ConnectApp requests.
    :ivar sid: The unique string that that we created to identify the ConnectApp resource.
    :ivar uri: The URI of the resource, relative to `https://api.twilio.com`.
    """

    def __init__(
        self,
        version: Version,
        payload: Dict[str, Any],
        account_sid: str,
        sid: Optional[str] = None,
    ):
        super().__init__(version)

        self.account_sid: Optional[str] = payload.get("account_sid")
        self.authorize_redirect_url: Optional[str] = payload.get(
            "authorize_redirect_url"
        )
        self.company_name: Optional[str] = payload.get("company_name")
        self.deauthorize_callback_method: Optional[str] = payload.get(
            "deauthorize_callback_method"
        )
        self.deauthorize_callback_url: Optional[str] = payload.get(
            "deauthorize_callback_url"
        )
        self.description: Optional[str] = payload.get("description")
        self.friendly_name: Optional[str] = payload.get("friendly_name")
        self.homepage_url: Optional[str] = payload.get("homepage_url")
        self.permissions: Optional[List["ConnectAppInstance.Permission"]] = payload.get(
            "permissions"
        )
        self.sid: Optional[str] = payload.get("sid")
        self.uri: Optional[str] = payload.get("uri")

        self._solution = {
            "account_sid": account_sid,
            "sid": sid or self.sid,
        }
        self._context: Optional[ConnectAppContext] = None

    @property
    def _proxy(self) -> "ConnectAppContext":
        """
        Generate an instance context for the instance, the context is capable of
        performing various actions. All instance actions are proxied to the context

        :returns: ConnectAppContext for this ConnectAppInstance
        """
        if self._context is None:
            self._context = ConnectAppContext(
                self._version,
                account_sid=self._solution["account_sid"],
                sid=self._solution["sid"],
            )
        return self._context

    def delete(self) -> bool:
        """
        Deletes the ConnectAppInstance


        :returns: True if delete succeeds, False otherwise
        """
        return self._proxy.delete()

    async def delete_async(self) -> bool:
        """
        Asynchronous coroutine that deletes the ConnectAppInstance


        :returns: True if delete succeeds, False otherwise
        """
        return await self._proxy.delete_async()

    def fetch(self) -> "ConnectAppInstance":
        """
        Fetch the ConnectAppInstance


        :returns: The fetched ConnectAppInstance
        """
        return self._proxy.fetch()

    async def fetch_async(self) -> "ConnectAppInstance":
        """
        Asynchronous coroutine to fetch the ConnectAppInstance


        :returns: The fetched ConnectAppInstance
        """
        return await self._proxy.fetch_async()

    def update(
        self,
        authorize_redirect_url: Union[str, object] = values.unset,
        company_name: Union[str, object] = values.unset,
        deauthorize_callback_method: Union[str, object] = values.unset,
        deauthorize_callback_url: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        friendly_name: Union[str, object] = values.unset,
        homepage_url: Union[str, object] = values.unset,
        permissions: Union[
            List["ConnectAppInstance.Permission"], object
        ] = values.unset,
    ) -> "ConnectAppInstance":
        """
        Update the ConnectAppInstance

        :param authorize_redirect_url: The URL to redirect the user to after we authenticate the user and obtain authorization to access the Connect App.
        :param company_name: The company name to set for the Connect App.
        :param deauthorize_callback_method: The HTTP method to use when calling `deauthorize_callback_url`.
        :param deauthorize_callback_url: The URL to call using the `deauthorize_callback_method` to de-authorize the Connect App.
        :param description: A description of the Connect App.
        :param friendly_name: A descriptive string that you create to describe the resource. It can be up to 64 characters long.
        :param homepage_url: A public URL where users can obtain more information about this Connect App.
        :param permissions: A comma-separated list of the permissions you will request from the users of this ConnectApp.  Can include: `get-all` and `post-all`.

        :returns: The updated ConnectAppInstance
        """
        return self._proxy.update(
            authorize_redirect_url=authorize_redirect_url,
            company_name=company_name,
            deauthorize_callback_method=deauthorize_callback_method,
            deauthorize_callback_url=deauthorize_callback_url,
            description=description,
            friendly_name=friendly_name,
            homepage_url=homepage_url,
            permissions=permissions,
        )

    async def update_async(
        self,
        authorize_redirect_url: Union[str, object] = values.unset,
        company_name: Union[str, object] = values.unset,
        deauthorize_callback_method: Union[str, object] = values.unset,
        deauthorize_callback_url: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        friendly_name: Union[str, object] = values.unset,
        homepage_url: Union[str, object] = values.unset,
        permissions: Union[
            List["ConnectAppInstance.Permission"], object
        ] = values.unset,
    ) -> "ConnectAppInstance":
        """
        Asynchronous coroutine to update the ConnectAppInstance

        :param authorize_redirect_url: The URL to redirect the user to after we authenticate the user and obtain authorization to access the Connect App.
        :param company_name: The company name to set for the Connect App.
        :param deauthorize_callback_method: The HTTP method to use when calling `deauthorize_callback_url`.
        :param deauthorize_callback_url: The URL to call using the `deauthorize_callback_method` to de-authorize the Connect App.
        :param description: A description of the Connect App.
        :param friendly_name: A descriptive string that you create to describe the resource. It can be up to 64 characters long.
        :param homepage_url: A public URL where users can obtain more information about this Connect App.
        :param permissions: A comma-separated list of the permissions you will request from the users of this ConnectApp.  Can include: `get-all` and `post-all`.

        :returns: The updated ConnectAppInstance
        """
        return await self._proxy.update_async(
            authorize_redirect_url=authorize_redirect_url,
            company_name=company_name,
            deauthorize_callback_method=deauthorize_callback_method,
            deauthorize_callback_url=deauthorize_callback_url,
            description=description,
            friendly_name=friendly_name,
            homepage_url=homepage_url,
            permissions=permissions,
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.Api.V2010.ConnectAppInstance {}>".format(context)


class ConnectAppContext(InstanceContext):

    def __init__(self, version: Version, account_sid: str, sid: str):
        """
        Initialize the ConnectAppContext

        :param version: Version that contains the resource
        :param account_sid: The SID of the [Account](https://www.twilio.com/docs/iam/api/account) that created the ConnectApp resources to update.
        :param sid: The Twilio-provided string that uniquely identifies the ConnectApp resource to update.
        """
        super().__init__(version)

        # Path Solution
        self._solution = {
            "account_sid": account_sid,
            "sid": sid,
        }
        self._uri = "/Accounts/{account_sid}/ConnectApps/{sid}.json".format(
            **self._solution
        )

    def delete(self) -> bool:
        """
        Deletes the ConnectAppInstance


        :returns: True if delete succeeds, False otherwise
        """

        headers = values.of({})

        return self._version.delete(method="DELETE", uri=self._uri, headers=headers)

    async def delete_async(self) -> bool:
        """
        Asynchronous coroutine that deletes the ConnectAppInstance


        :returns: True if delete succeeds, False otherwise
        """

        headers = values.of({})

        return await self._version.delete_async(
            method="DELETE", uri=self._uri, headers=headers
        )

    def fetch(self) -> ConnectAppInstance:
        """
        Fetch the ConnectAppInstance


        :returns: The fetched ConnectAppInstance
        """

        headers = values.of({})

        headers["Accept"] = "application/json"

        payload = self._version.fetch(method="GET", uri=self._uri, headers=headers)

        return ConnectAppInstance(
            self._version,
            payload,
            account_sid=self._solution["account_sid"],
            sid=self._solution["sid"],
        )

    async def fetch_async(self) -> ConnectAppInstance:
        """
        Asynchronous coroutine to fetch the ConnectAppInstance


        :returns: The fetched ConnectAppInstance
        """

        headers = values.of({})

        headers["Accept"] = "application/json"

        payload = await self._version.fetch_async(
            method="GET", uri=self._uri, headers=headers
        )

        return ConnectAppInstance(
            self._version,
            payload,
            account_sid=self._solution["account_sid"],
            sid=self._solution["sid"],
        )

    def update(
        self,
        authorize_redirect_url: Union[str, object] = values.unset,
        company_name: Union[str, object] = values.unset,
        deauthorize_callback_method: Union[str, object] = values.unset,
        deauthorize_callback_url: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        friendly_name: Union[str, object] = values.unset,
        homepage_url: Union[str, object] = values.unset,
        permissions: Union[
            List["ConnectAppInstance.Permission"], object
        ] = values.unset,
    ) -> ConnectAppInstance:
        """
        Update the ConnectAppInstance

        :param authorize_redirect_url: The URL to redirect the user to after we authenticate the user and obtain authorization to access the Connect App.
        :param company_name: The company name to set for the Connect App.
        :param deauthorize_callback_method: The HTTP method to use when calling `deauthorize_callback_url`.
        :param deauthorize_callback_url: The URL to call using the `deauthorize_callback_method` to de-authorize the Connect App.
        :param description: A description of the Connect App.
        :param friendly_name: A descriptive string that you create to describe the resource. It can be up to 64 characters long.
        :param homepage_url: A public URL where users can obtain more information about this Connect App.
        :param permissions: A comma-separated list of the permissions you will request from the users of this ConnectApp.  Can include: `get-all` and `post-all`.

        :returns: The updated ConnectAppInstance
        """

        data = values.of(
            {
                "AuthorizeRedirectUrl": authorize_redirect_url,
                "CompanyName": company_name,
                "DeauthorizeCallbackMethod": deauthorize_callback_method,
                "DeauthorizeCallbackUrl": deauthorize_callback_url,
                "Description": description,
                "FriendlyName": friendly_name,
                "HomepageUrl": homepage_url,
                "Permissions": serialize.map(permissions, lambda e: e),
            }
        )
        headers = values.of({})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = self._version.update(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return ConnectAppInstance(
            self._version,
            payload,
            account_sid=self._solution["account_sid"],
            sid=self._solution["sid"],
        )

    async def update_async(
        self,
        authorize_redirect_url: Union[str, object] = values.unset,
        company_name: Union[str, object] = values.unset,
        deauthorize_callback_method: Union[str, object] = values.unset,
        deauthorize_callback_url: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        friendly_name: Union[str, object] = values.unset,
        homepage_url: Union[str, object] = values.unset,
        permissions: Union[
            List["ConnectAppInstance.Permission"], object
        ] = values.unset,
    ) -> ConnectAppInstance:
        """
        Asynchronous coroutine to update the ConnectAppInstance

        :param authorize_redirect_url: The URL to redirect the user to after we authenticate the user and obtain authorization to access the Connect App.
        :param company_name: The company name to set for the Connect App.
        :param deauthorize_callback_method: The HTTP method to use when calling `deauthorize_callback_url`.
        :param deauthorize_callback_url: The URL to call using the `deauthorize_callback_method` to de-authorize the Connect App.
        :param description: A description of the Connect App.
        :param friendly_name: A descriptive string that you create to describe the resource. It can be up to 64 characters long.
        :param homepage_url: A public URL where users can obtain more information about this Connect App.
        :param permissions: A comma-separated list of the permissions you will request from the users of this ConnectApp.  Can include: `get-all` and `post-all`.

        :returns: The updated ConnectAppInstance
        """

        data = values.of(
            {
                "AuthorizeRedirectUrl": authorize_redirect_url,
                "CompanyName": company_name,
                "DeauthorizeCallbackMethod": deauthorize_callback_method,
                "DeauthorizeCallbackUrl": deauthorize_callback_url,
                "Description": description,
                "FriendlyName": friendly_name,
                "HomepageUrl": homepage_url,
                "Permissions": serialize.map(permissions, lambda e: e),
            }
        )
        headers = values.of({})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = await self._version.update_async(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return ConnectAppInstance(
            self._version,
            payload,
            account_sid=self._solution["account_sid"],
            sid=self._solution["sid"],
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.Api.V2010.ConnectAppContext {}>".format(context)


class ConnectAppPage(Page):

    def get_instance(self, payload: Dict[str, Any]) -> ConnectAppInstance:
        """
        Build an instance of ConnectAppInstance

        :param payload: Payload response from the API
        """
        return ConnectAppInstance(
            self._version, payload, account_sid=self._solution["account_sid"]
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.Api.V2010.ConnectAppPage>"


class ConnectAppList(ListResource):

    def __init__(self, version: Version, account_sid: str):
        """
        Initialize the ConnectAppList

        :param version: Version that contains the resource
        :param account_sid: The SID of the [Account](https://www.twilio.com/docs/iam/api/account) that created the ConnectApp resources to read.

        """
        super().__init__(version)

        # Path Solution
        self._solution = {
            "account_sid": account_sid,
        }
        self._uri = "/Accounts/{account_sid}/ConnectApps.json".format(**self._solution)

    def stream(
        self,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Iterator[ConnectAppInstance]:
        """
        Streams ConnectAppInstance records from the API as a generator stream.
        This operation lazily loads records as efficiently as possible until the limit
        is reached.
        The results are returned as a generator, so this operation is memory efficient.

        :param limit: Upper limit for the number of records to return. stream()
                      guarantees to never return more than limit.  Default is no limit
        :param page_size: Number of records to fetch per request, when not set will use
                          the default value of 50 records.  If no page_size is defined
                          but a limit is defined, stream() will attempt to read the
                          limit with the most efficient page size, i.e. min(limit, 1000)

        :returns: Generator that will yield up to limit results
        """
        limits = self._version.read_limits(limit, page_size)
        page = self.page(page_size=limits["page_size"])

        return self._version.stream(page, limits["limit"])

    async def stream_async(
        self,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> AsyncIterator[ConnectAppInstance]:
        """
        Asynchronously streams ConnectAppInstance records from the API as a generator stream.
        This operation lazily loads records as efficiently as possible until the limit
        is reached.
        The results are returned as a generator, so this operation is memory efficient.

        :param limit: Upper limit for the number of records to return. stream()
                      guarantees to never return more than limit.  Default is no limit
        :param page_size: Number of records to fetch per request, when not set will use
                          the default value of 50 records.  If no page_size is defined
                          but a limit is defined, stream() will attempt to read the
                          limit with the most efficient page size, i.e. min(limit, 1000)

        :returns: Generator that will yield up to limit results
        """
        limits = self._version.read_limits(limit, page_size)
        page = await self.page_async(page_size=limits["page_size"])

        return self._version.stream_async(page, limits["limit"])

    def list(
        self,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[ConnectAppInstance]:
        """
        Lists ConnectAppInstance records from the API as a list.
        Unlike stream(), this operation is eager and will load `limit` records into
        memory before returning.

        :param limit: Upper limit for the number of records to return. list() guarantees
                      never to return more than limit.  Default is no limit
        :param page_size: Number of records to fetch per request, when not set will use
                          the default value of 50 records.  If no page_size is defined
                          but a limit is defined, list() will attempt to read the limit
                          with the most efficient page size, i.e. min(limit, 1000)

        :returns: list that will contain up to limit results
        """
        return list(
            self.stream(
                limit=limit,
                page_size=page_size,
            )
        )

    async def list_async(
        self,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[ConnectAppInstance]:
        """
        Asynchronously lists ConnectAppInstance records from the API as a list.
        Unlike stream(), this operation is eager and will load `limit` records into
        memory before returning.

        :param limit: Upper limit for the number of records to return. list() guarantees
                      never to return more than limit.  Default is no limit
        :param page_size: Number of records to fetch per request, when not set will use
                          the default value of 50 records.  If no page_size is defined
                          but a limit is defined, list() will attempt to read the limit
                          with the most efficient page size, i.e. min(limit, 1000)

        :returns: list that will contain up to limit results
        """
        return [
            record
            async for record in await self.stream_async(
                limit=limit,
                page_size=page_size,
            )
        ]

    def page(
        self,
        page_token: Union[str, object] = values.unset,
        page_number: Union[int, object] = values.unset,
        page_size: Union[int, object] = values.unset,
    ) -> ConnectAppPage:
        """
        Retrieve a single page of ConnectAppInstance records from the API.
        Request is executed immediately

        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of ConnectAppInstance
        """
        data = values.of(
            {
                "PageToken": page_token,
                "Page": page_number,
                "PageSize": page_size,
            }
        )

        headers = values.of({"Content-Type": "application/x-www-form-urlencoded"})

        headers["Accept"] = "application/json"

        response = self._version.page(
            method="GET", uri=self._uri, params=data, headers=headers
        )
        return ConnectAppPage(self._version, response, self._solution)

    async def page_async(
        self,
        page_token: Union[str, object] = values.unset,
        page_number: Union[int, object] = values.unset,
        page_size: Union[int, object] = values.unset,
    ) -> ConnectAppPage:
        """
        Asynchronously retrieve a single page of ConnectAppInstance records from the API.
        Request is executed immediately

        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of ConnectAppInstance
        """
        data = values.of(
            {
                "PageToken": page_token,
                "Page": page_number,
                "PageSize": page_size,
            }
        )

        headers = values.of({"Content-Type": "application/x-www-form-urlencoded"})

        headers["Accept"] = "application/json"

        response = await self._version.page_async(
            method="GET", uri=self._uri, params=data, headers=headers
        )
        return ConnectAppPage(self._version, response, self._solution)

    def get_page(self, target_url: str) -> ConnectAppPage:
        """
        Retrieve a specific page of ConnectAppInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of ConnectAppInstance
        """
        response = self._version.domain.twilio.request("GET", target_url)
        return ConnectAppPage(self._version, response, self._solution)

    async def get_page_async(self, target_url: str) -> ConnectAppPage:
        """
        Asynchronously retrieve a specific page of ConnectAppInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of ConnectAppInstance
        """
        response = await self._version.domain.twilio.request_async("GET", target_url)
        return ConnectAppPage(self._version, response, self._solution)

    def get(self, sid: str) -> ConnectAppContext:
        """
        Constructs a ConnectAppContext

        :param sid: The Twilio-provided string that uniquely identifies the ConnectApp resource to update.
        """
        return ConnectAppContext(
            self._version, account_sid=self._solution["account_sid"], sid=sid
        )

    def __call__(self, sid: str) -> ConnectAppContext:
        """
        Constructs a ConnectAppContext

        :param sid: The Twilio-provided string that uniquely identifies the ConnectApp resource to update.
        """
        return ConnectAppContext(
            self._version, account_sid=self._solution["account_sid"], sid=sid
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.Api.V2010.ConnectAppList>"
