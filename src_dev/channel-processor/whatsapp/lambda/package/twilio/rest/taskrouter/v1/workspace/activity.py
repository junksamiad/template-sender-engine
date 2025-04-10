r"""
    This code was generated by
   ___ _ _ _ _ _    _ ____    ____ ____ _    ____ ____ _  _ ____ ____ ____ ___ __   __
    |  | | | | |    | |  | __ |  | |__| | __ | __ |___ |\ | |___ |__/ |__|  | |  | |__/
    |  |_|_| | |___ | |__|    |__| |  | |    |__] |___ | \| |___ |  \ |  |  | |__| |  \

    Twilio - Taskrouter
    This is the public Twilio REST API.

    NOTE: This class is auto generated by OpenAPI Generator.
    https://openapi-generator.tech
    Do not edit the class manually.
"""

from datetime import datetime
from typing import Any, Dict, List, Optional, Union, Iterator, AsyncIterator
from twilio.base import deserialize, serialize, values
from twilio.base.instance_context import InstanceContext
from twilio.base.instance_resource import InstanceResource
from twilio.base.list_resource import ListResource
from twilio.base.version import Version
from twilio.base.page import Page


class ActivityInstance(InstanceResource):
    """
    :ivar account_sid: The SID of the [Account](https://www.twilio.com/docs/iam/api/account) that created the Activity resource.
    :ivar available: Whether the Worker is eligible to receive a Task when it occupies the Activity. A value of `true`, `1`, or `yes` indicates the Activity is available. All other values indicate that it is not. The value cannot be changed after the Activity is created.
    :ivar date_created: The date and time in GMT when the resource was created specified in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format.
    :ivar date_updated: The date and time in GMT when the resource was last updated specified in [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) format.
    :ivar friendly_name: The string that you assigned to describe the Activity resource.
    :ivar sid: The unique string that we created to identify the Activity resource.
    :ivar workspace_sid: The SID of the Workspace that contains the Activity.
    :ivar url: The absolute URL of the Activity resource.
    :ivar links:
    """

    def __init__(
        self,
        version: Version,
        payload: Dict[str, Any],
        workspace_sid: str,
        sid: Optional[str] = None,
    ):
        super().__init__(version)

        self.account_sid: Optional[str] = payload.get("account_sid")
        self.available: Optional[bool] = payload.get("available")
        self.date_created: Optional[datetime] = deserialize.iso8601_datetime(
            payload.get("date_created")
        )
        self.date_updated: Optional[datetime] = deserialize.iso8601_datetime(
            payload.get("date_updated")
        )
        self.friendly_name: Optional[str] = payload.get("friendly_name")
        self.sid: Optional[str] = payload.get("sid")
        self.workspace_sid: Optional[str] = payload.get("workspace_sid")
        self.url: Optional[str] = payload.get("url")
        self.links: Optional[Dict[str, object]] = payload.get("links")

        self._solution = {
            "workspace_sid": workspace_sid,
            "sid": sid or self.sid,
        }
        self._context: Optional[ActivityContext] = None

    @property
    def _proxy(self) -> "ActivityContext":
        """
        Generate an instance context for the instance, the context is capable of
        performing various actions. All instance actions are proxied to the context

        :returns: ActivityContext for this ActivityInstance
        """
        if self._context is None:
            self._context = ActivityContext(
                self._version,
                workspace_sid=self._solution["workspace_sid"],
                sid=self._solution["sid"],
            )
        return self._context

    def delete(self) -> bool:
        """
        Deletes the ActivityInstance


        :returns: True if delete succeeds, False otherwise
        """
        return self._proxy.delete()

    async def delete_async(self) -> bool:
        """
        Asynchronous coroutine that deletes the ActivityInstance


        :returns: True if delete succeeds, False otherwise
        """
        return await self._proxy.delete_async()

    def fetch(self) -> "ActivityInstance":
        """
        Fetch the ActivityInstance


        :returns: The fetched ActivityInstance
        """
        return self._proxy.fetch()

    async def fetch_async(self) -> "ActivityInstance":
        """
        Asynchronous coroutine to fetch the ActivityInstance


        :returns: The fetched ActivityInstance
        """
        return await self._proxy.fetch_async()

    def update(
        self, friendly_name: Union[str, object] = values.unset
    ) -> "ActivityInstance":
        """
        Update the ActivityInstance

        :param friendly_name: A descriptive string that you create to describe the Activity resource. It can be up to 64 characters long. These names are used to calculate and expose statistics about Workers, and provide visibility into the state of each Worker. Examples of friendly names include: `on-call`, `break`, and `email`.

        :returns: The updated ActivityInstance
        """
        return self._proxy.update(
            friendly_name=friendly_name,
        )

    async def update_async(
        self, friendly_name: Union[str, object] = values.unset
    ) -> "ActivityInstance":
        """
        Asynchronous coroutine to update the ActivityInstance

        :param friendly_name: A descriptive string that you create to describe the Activity resource. It can be up to 64 characters long. These names are used to calculate and expose statistics about Workers, and provide visibility into the state of each Worker. Examples of friendly names include: `on-call`, `break`, and `email`.

        :returns: The updated ActivityInstance
        """
        return await self._proxy.update_async(
            friendly_name=friendly_name,
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.Taskrouter.V1.ActivityInstance {}>".format(context)


class ActivityContext(InstanceContext):

    def __init__(self, version: Version, workspace_sid: str, sid: str):
        """
        Initialize the ActivityContext

        :param version: Version that contains the resource
        :param workspace_sid: The SID of the Workspace with the Activity resources to update.
        :param sid: The SID of the Activity resource to update.
        """
        super().__init__(version)

        # Path Solution
        self._solution = {
            "workspace_sid": workspace_sid,
            "sid": sid,
        }
        self._uri = "/Workspaces/{workspace_sid}/Activities/{sid}".format(
            **self._solution
        )

    def delete(self) -> bool:
        """
        Deletes the ActivityInstance


        :returns: True if delete succeeds, False otherwise
        """

        headers = values.of({})

        return self._version.delete(method="DELETE", uri=self._uri, headers=headers)

    async def delete_async(self) -> bool:
        """
        Asynchronous coroutine that deletes the ActivityInstance


        :returns: True if delete succeeds, False otherwise
        """

        headers = values.of({})

        return await self._version.delete_async(
            method="DELETE", uri=self._uri, headers=headers
        )

    def fetch(self) -> ActivityInstance:
        """
        Fetch the ActivityInstance


        :returns: The fetched ActivityInstance
        """

        headers = values.of({})

        headers["Accept"] = "application/json"

        payload = self._version.fetch(method="GET", uri=self._uri, headers=headers)

        return ActivityInstance(
            self._version,
            payload,
            workspace_sid=self._solution["workspace_sid"],
            sid=self._solution["sid"],
        )

    async def fetch_async(self) -> ActivityInstance:
        """
        Asynchronous coroutine to fetch the ActivityInstance


        :returns: The fetched ActivityInstance
        """

        headers = values.of({})

        headers["Accept"] = "application/json"

        payload = await self._version.fetch_async(
            method="GET", uri=self._uri, headers=headers
        )

        return ActivityInstance(
            self._version,
            payload,
            workspace_sid=self._solution["workspace_sid"],
            sid=self._solution["sid"],
        )

    def update(
        self, friendly_name: Union[str, object] = values.unset
    ) -> ActivityInstance:
        """
        Update the ActivityInstance

        :param friendly_name: A descriptive string that you create to describe the Activity resource. It can be up to 64 characters long. These names are used to calculate and expose statistics about Workers, and provide visibility into the state of each Worker. Examples of friendly names include: `on-call`, `break`, and `email`.

        :returns: The updated ActivityInstance
        """

        data = values.of(
            {
                "FriendlyName": friendly_name,
            }
        )
        headers = values.of({})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = self._version.update(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return ActivityInstance(
            self._version,
            payload,
            workspace_sid=self._solution["workspace_sid"],
            sid=self._solution["sid"],
        )

    async def update_async(
        self, friendly_name: Union[str, object] = values.unset
    ) -> ActivityInstance:
        """
        Asynchronous coroutine to update the ActivityInstance

        :param friendly_name: A descriptive string that you create to describe the Activity resource. It can be up to 64 characters long. These names are used to calculate and expose statistics about Workers, and provide visibility into the state of each Worker. Examples of friendly names include: `on-call`, `break`, and `email`.

        :returns: The updated ActivityInstance
        """

        data = values.of(
            {
                "FriendlyName": friendly_name,
            }
        )
        headers = values.of({})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = await self._version.update_async(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return ActivityInstance(
            self._version,
            payload,
            workspace_sid=self._solution["workspace_sid"],
            sid=self._solution["sid"],
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.Taskrouter.V1.ActivityContext {}>".format(context)


class ActivityPage(Page):

    def get_instance(self, payload: Dict[str, Any]) -> ActivityInstance:
        """
        Build an instance of ActivityInstance

        :param payload: Payload response from the API
        """
        return ActivityInstance(
            self._version, payload, workspace_sid=self._solution["workspace_sid"]
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.Taskrouter.V1.ActivityPage>"


class ActivityList(ListResource):

    def __init__(self, version: Version, workspace_sid: str):
        """
        Initialize the ActivityList

        :param version: Version that contains the resource
        :param workspace_sid: The SID of the Workspace with the Activity resources to read.

        """
        super().__init__(version)

        # Path Solution
        self._solution = {
            "workspace_sid": workspace_sid,
        }
        self._uri = "/Workspaces/{workspace_sid}/Activities".format(**self._solution)

    def create(
        self, friendly_name: str, available: Union[bool, object] = values.unset
    ) -> ActivityInstance:
        """
        Create the ActivityInstance

        :param friendly_name: A descriptive string that you create to describe the Activity resource. It can be up to 64 characters long. These names are used to calculate and expose statistics about Workers, and provide visibility into the state of each Worker. Examples of friendly names include: `on-call`, `break`, and `email`.
        :param available: Whether the Worker should be eligible to receive a Task when it occupies the Activity. A value of `true`, `1`, or `yes` specifies the Activity is available. All other values specify that it is not. The value cannot be changed after the Activity is created.

        :returns: The created ActivityInstance
        """

        data = values.of(
            {
                "FriendlyName": friendly_name,
                "Available": serialize.boolean_to_string(available),
            }
        )
        headers = values.of({"Content-Type": "application/x-www-form-urlencoded"})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = self._version.create(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return ActivityInstance(
            self._version, payload, workspace_sid=self._solution["workspace_sid"]
        )

    async def create_async(
        self, friendly_name: str, available: Union[bool, object] = values.unset
    ) -> ActivityInstance:
        """
        Asynchronously create the ActivityInstance

        :param friendly_name: A descriptive string that you create to describe the Activity resource. It can be up to 64 characters long. These names are used to calculate and expose statistics about Workers, and provide visibility into the state of each Worker. Examples of friendly names include: `on-call`, `break`, and `email`.
        :param available: Whether the Worker should be eligible to receive a Task when it occupies the Activity. A value of `true`, `1`, or `yes` specifies the Activity is available. All other values specify that it is not. The value cannot be changed after the Activity is created.

        :returns: The created ActivityInstance
        """

        data = values.of(
            {
                "FriendlyName": friendly_name,
                "Available": serialize.boolean_to_string(available),
            }
        )
        headers = values.of({"Content-Type": "application/x-www-form-urlencoded"})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = await self._version.create_async(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return ActivityInstance(
            self._version, payload, workspace_sid=self._solution["workspace_sid"]
        )

    def stream(
        self,
        friendly_name: Union[str, object] = values.unset,
        available: Union[str, object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Iterator[ActivityInstance]:
        """
        Streams ActivityInstance records from the API as a generator stream.
        This operation lazily loads records as efficiently as possible until the limit
        is reached.
        The results are returned as a generator, so this operation is memory efficient.

        :param str friendly_name: The `friendly_name` of the Activity resources to read.
        :param str available: Whether return only Activity resources that are available or unavailable. A value of `true` returns only available activities. Values of '1' or `yes` also indicate `true`. All other values represent `false` and return activities that are unavailable.
        :param limit: Upper limit for the number of records to return. stream()
                      guarantees to never return more than limit.  Default is no limit
        :param page_size: Number of records to fetch per request, when not set will use
                          the default value of 50 records.  If no page_size is defined
                          but a limit is defined, stream() will attempt to read the
                          limit with the most efficient page size, i.e. min(limit, 1000)

        :returns: Generator that will yield up to limit results
        """
        limits = self._version.read_limits(limit, page_size)
        page = self.page(
            friendly_name=friendly_name,
            available=available,
            page_size=limits["page_size"],
        )

        return self._version.stream(page, limits["limit"])

    async def stream_async(
        self,
        friendly_name: Union[str, object] = values.unset,
        available: Union[str, object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> AsyncIterator[ActivityInstance]:
        """
        Asynchronously streams ActivityInstance records from the API as a generator stream.
        This operation lazily loads records as efficiently as possible until the limit
        is reached.
        The results are returned as a generator, so this operation is memory efficient.

        :param str friendly_name: The `friendly_name` of the Activity resources to read.
        :param str available: Whether return only Activity resources that are available or unavailable. A value of `true` returns only available activities. Values of '1' or `yes` also indicate `true`. All other values represent `false` and return activities that are unavailable.
        :param limit: Upper limit for the number of records to return. stream()
                      guarantees to never return more than limit.  Default is no limit
        :param page_size: Number of records to fetch per request, when not set will use
                          the default value of 50 records.  If no page_size is defined
                          but a limit is defined, stream() will attempt to read the
                          limit with the most efficient page size, i.e. min(limit, 1000)

        :returns: Generator that will yield up to limit results
        """
        limits = self._version.read_limits(limit, page_size)
        page = await self.page_async(
            friendly_name=friendly_name,
            available=available,
            page_size=limits["page_size"],
        )

        return self._version.stream_async(page, limits["limit"])

    def list(
        self,
        friendly_name: Union[str, object] = values.unset,
        available: Union[str, object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[ActivityInstance]:
        """
        Lists ActivityInstance records from the API as a list.
        Unlike stream(), this operation is eager and will load `limit` records into
        memory before returning.

        :param str friendly_name: The `friendly_name` of the Activity resources to read.
        :param str available: Whether return only Activity resources that are available or unavailable. A value of `true` returns only available activities. Values of '1' or `yes` also indicate `true`. All other values represent `false` and return activities that are unavailable.
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
                friendly_name=friendly_name,
                available=available,
                limit=limit,
                page_size=page_size,
            )
        )

    async def list_async(
        self,
        friendly_name: Union[str, object] = values.unset,
        available: Union[str, object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[ActivityInstance]:
        """
        Asynchronously lists ActivityInstance records from the API as a list.
        Unlike stream(), this operation is eager and will load `limit` records into
        memory before returning.

        :param str friendly_name: The `friendly_name` of the Activity resources to read.
        :param str available: Whether return only Activity resources that are available or unavailable. A value of `true` returns only available activities. Values of '1' or `yes` also indicate `true`. All other values represent `false` and return activities that are unavailable.
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
                friendly_name=friendly_name,
                available=available,
                limit=limit,
                page_size=page_size,
            )
        ]

    def page(
        self,
        friendly_name: Union[str, object] = values.unset,
        available: Union[str, object] = values.unset,
        page_token: Union[str, object] = values.unset,
        page_number: Union[int, object] = values.unset,
        page_size: Union[int, object] = values.unset,
    ) -> ActivityPage:
        """
        Retrieve a single page of ActivityInstance records from the API.
        Request is executed immediately

        :param friendly_name: The `friendly_name` of the Activity resources to read.
        :param available: Whether return only Activity resources that are available or unavailable. A value of `true` returns only available activities. Values of '1' or `yes` also indicate `true`. All other values represent `false` and return activities that are unavailable.
        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of ActivityInstance
        """
        data = values.of(
            {
                "FriendlyName": friendly_name,
                "Available": available,
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
        return ActivityPage(self._version, response, self._solution)

    async def page_async(
        self,
        friendly_name: Union[str, object] = values.unset,
        available: Union[str, object] = values.unset,
        page_token: Union[str, object] = values.unset,
        page_number: Union[int, object] = values.unset,
        page_size: Union[int, object] = values.unset,
    ) -> ActivityPage:
        """
        Asynchronously retrieve a single page of ActivityInstance records from the API.
        Request is executed immediately

        :param friendly_name: The `friendly_name` of the Activity resources to read.
        :param available: Whether return only Activity resources that are available or unavailable. A value of `true` returns only available activities. Values of '1' or `yes` also indicate `true`. All other values represent `false` and return activities that are unavailable.
        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of ActivityInstance
        """
        data = values.of(
            {
                "FriendlyName": friendly_name,
                "Available": available,
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
        return ActivityPage(self._version, response, self._solution)

    def get_page(self, target_url: str) -> ActivityPage:
        """
        Retrieve a specific page of ActivityInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of ActivityInstance
        """
        response = self._version.domain.twilio.request("GET", target_url)
        return ActivityPage(self._version, response, self._solution)

    async def get_page_async(self, target_url: str) -> ActivityPage:
        """
        Asynchronously retrieve a specific page of ActivityInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of ActivityInstance
        """
        response = await self._version.domain.twilio.request_async("GET", target_url)
        return ActivityPage(self._version, response, self._solution)

    def get(self, sid: str) -> ActivityContext:
        """
        Constructs a ActivityContext

        :param sid: The SID of the Activity resource to update.
        """
        return ActivityContext(
            self._version, workspace_sid=self._solution["workspace_sid"], sid=sid
        )

    def __call__(self, sid: str) -> ActivityContext:
        """
        Constructs a ActivityContext

        :param sid: The SID of the Activity resource to update.
        """
        return ActivityContext(
            self._version, workspace_sid=self._solution["workspace_sid"], sid=sid
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.Taskrouter.V1.ActivityList>"
