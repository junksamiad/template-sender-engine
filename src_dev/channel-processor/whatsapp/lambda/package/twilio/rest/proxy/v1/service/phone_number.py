r"""
    This code was generated by
   ___ _ _ _ _ _    _ ____    ____ ____ _    ____ ____ _  _ ____ ____ ____ ___ __   __
    |  | | | | |    | |  | __ |  | |__| | __ | __ |___ |\ | |___ |__/ |__|  | |  | |__/
    |  |_|_| | |___ | |__|    |__| |  | |    |__] |___ | \| |___ |  \ |  |  | |__| |  \

    Twilio - Proxy
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


class PhoneNumberInstance(InstanceResource):
    """
    :ivar sid: The unique string that we created to identify the PhoneNumber resource.
    :ivar account_sid: The SID of the [Account](https://www.twilio.com/docs/iam/api/account) that created the PhoneNumber resource.
    :ivar service_sid: The SID of the PhoneNumber resource's parent [Service](https://www.twilio.com/docs/proxy/api/service) resource.
    :ivar date_created: The [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) date and time in GMT when the resource was created.
    :ivar date_updated: The [ISO 8601](https://en.wikipedia.org/wiki/ISO_8601) date and time in GMT when the resource was last updated.
    :ivar phone_number: The phone number in [E.164](https://www.twilio.com/docs/glossary/what-e164) format, which consists of a + followed by the country code and subscriber number.
    :ivar friendly_name: The string that you assigned to describe the resource.
    :ivar iso_country: The ISO Country Code for the phone number.
    :ivar capabilities:
    :ivar url: The absolute URL of the PhoneNumber resource.
    :ivar is_reserved: Whether the phone number should be reserved and not be assigned to a participant using proxy pool logic. See [Reserved Phone Numbers](https://www.twilio.com/docs/proxy/reserved-phone-numbers) for more information.
    :ivar in_use: The number of open session assigned to the number. See the [How many Phone Numbers do I need?](https://www.twilio.com/docs/proxy/phone-numbers-needed) guide for more information.
    """

    def __init__(
        self,
        version: Version,
        payload: Dict[str, Any],
        service_sid: str,
        sid: Optional[str] = None,
    ):
        super().__init__(version)

        self.sid: Optional[str] = payload.get("sid")
        self.account_sid: Optional[str] = payload.get("account_sid")
        self.service_sid: Optional[str] = payload.get("service_sid")
        self.date_created: Optional[datetime] = deserialize.iso8601_datetime(
            payload.get("date_created")
        )
        self.date_updated: Optional[datetime] = deserialize.iso8601_datetime(
            payload.get("date_updated")
        )
        self.phone_number: Optional[str] = payload.get("phone_number")
        self.friendly_name: Optional[str] = payload.get("friendly_name")
        self.iso_country: Optional[str] = payload.get("iso_country")
        self.capabilities: Optional[str] = payload.get("capabilities")
        self.url: Optional[str] = payload.get("url")
        self.is_reserved: Optional[bool] = payload.get("is_reserved")
        self.in_use: Optional[int] = deserialize.integer(payload.get("in_use"))

        self._solution = {
            "service_sid": service_sid,
            "sid": sid or self.sid,
        }
        self._context: Optional[PhoneNumberContext] = None

    @property
    def _proxy(self) -> "PhoneNumberContext":
        """
        Generate an instance context for the instance, the context is capable of
        performing various actions. All instance actions are proxied to the context

        :returns: PhoneNumberContext for this PhoneNumberInstance
        """
        if self._context is None:
            self._context = PhoneNumberContext(
                self._version,
                service_sid=self._solution["service_sid"],
                sid=self._solution["sid"],
            )
        return self._context

    def delete(self) -> bool:
        """
        Deletes the PhoneNumberInstance


        :returns: True if delete succeeds, False otherwise
        """
        return self._proxy.delete()

    async def delete_async(self) -> bool:
        """
        Asynchronous coroutine that deletes the PhoneNumberInstance


        :returns: True if delete succeeds, False otherwise
        """
        return await self._proxy.delete_async()

    def fetch(self) -> "PhoneNumberInstance":
        """
        Fetch the PhoneNumberInstance


        :returns: The fetched PhoneNumberInstance
        """
        return self._proxy.fetch()

    async def fetch_async(self) -> "PhoneNumberInstance":
        """
        Asynchronous coroutine to fetch the PhoneNumberInstance


        :returns: The fetched PhoneNumberInstance
        """
        return await self._proxy.fetch_async()

    def update(
        self, is_reserved: Union[bool, object] = values.unset
    ) -> "PhoneNumberInstance":
        """
        Update the PhoneNumberInstance

        :param is_reserved: Whether the phone number should be reserved and not be assigned to a participant using proxy pool logic. See [Reserved Phone Numbers](https://www.twilio.com/docs/proxy/reserved-phone-numbers) for more information.

        :returns: The updated PhoneNumberInstance
        """
        return self._proxy.update(
            is_reserved=is_reserved,
        )

    async def update_async(
        self, is_reserved: Union[bool, object] = values.unset
    ) -> "PhoneNumberInstance":
        """
        Asynchronous coroutine to update the PhoneNumberInstance

        :param is_reserved: Whether the phone number should be reserved and not be assigned to a participant using proxy pool logic. See [Reserved Phone Numbers](https://www.twilio.com/docs/proxy/reserved-phone-numbers) for more information.

        :returns: The updated PhoneNumberInstance
        """
        return await self._proxy.update_async(
            is_reserved=is_reserved,
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.Proxy.V1.PhoneNumberInstance {}>".format(context)


class PhoneNumberContext(InstanceContext):

    def __init__(self, version: Version, service_sid: str, sid: str):
        """
        Initialize the PhoneNumberContext

        :param version: Version that contains the resource
        :param service_sid: The SID of the parent [Service](https://www.twilio.com/docs/proxy/api/service) of the PhoneNumber resource to update.
        :param sid: The Twilio-provided string that uniquely identifies the PhoneNumber resource to update.
        """
        super().__init__(version)

        # Path Solution
        self._solution = {
            "service_sid": service_sid,
            "sid": sid,
        }
        self._uri = "/Services/{service_sid}/PhoneNumbers/{sid}".format(
            **self._solution
        )

    def delete(self) -> bool:
        """
        Deletes the PhoneNumberInstance


        :returns: True if delete succeeds, False otherwise
        """

        headers = values.of({})

        return self._version.delete(method="DELETE", uri=self._uri, headers=headers)

    async def delete_async(self) -> bool:
        """
        Asynchronous coroutine that deletes the PhoneNumberInstance


        :returns: True if delete succeeds, False otherwise
        """

        headers = values.of({})

        return await self._version.delete_async(
            method="DELETE", uri=self._uri, headers=headers
        )

    def fetch(self) -> PhoneNumberInstance:
        """
        Fetch the PhoneNumberInstance


        :returns: The fetched PhoneNumberInstance
        """

        headers = values.of({})

        headers["Accept"] = "application/json"

        payload = self._version.fetch(method="GET", uri=self._uri, headers=headers)

        return PhoneNumberInstance(
            self._version,
            payload,
            service_sid=self._solution["service_sid"],
            sid=self._solution["sid"],
        )

    async def fetch_async(self) -> PhoneNumberInstance:
        """
        Asynchronous coroutine to fetch the PhoneNumberInstance


        :returns: The fetched PhoneNumberInstance
        """

        headers = values.of({})

        headers["Accept"] = "application/json"

        payload = await self._version.fetch_async(
            method="GET", uri=self._uri, headers=headers
        )

        return PhoneNumberInstance(
            self._version,
            payload,
            service_sid=self._solution["service_sid"],
            sid=self._solution["sid"],
        )

    def update(
        self, is_reserved: Union[bool, object] = values.unset
    ) -> PhoneNumberInstance:
        """
        Update the PhoneNumberInstance

        :param is_reserved: Whether the phone number should be reserved and not be assigned to a participant using proxy pool logic. See [Reserved Phone Numbers](https://www.twilio.com/docs/proxy/reserved-phone-numbers) for more information.

        :returns: The updated PhoneNumberInstance
        """

        data = values.of(
            {
                "IsReserved": serialize.boolean_to_string(is_reserved),
            }
        )
        headers = values.of({})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = self._version.update(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return PhoneNumberInstance(
            self._version,
            payload,
            service_sid=self._solution["service_sid"],
            sid=self._solution["sid"],
        )

    async def update_async(
        self, is_reserved: Union[bool, object] = values.unset
    ) -> PhoneNumberInstance:
        """
        Asynchronous coroutine to update the PhoneNumberInstance

        :param is_reserved: Whether the phone number should be reserved and not be assigned to a participant using proxy pool logic. See [Reserved Phone Numbers](https://www.twilio.com/docs/proxy/reserved-phone-numbers) for more information.

        :returns: The updated PhoneNumberInstance
        """

        data = values.of(
            {
                "IsReserved": serialize.boolean_to_string(is_reserved),
            }
        )
        headers = values.of({})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = await self._version.update_async(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return PhoneNumberInstance(
            self._version,
            payload,
            service_sid=self._solution["service_sid"],
            sid=self._solution["sid"],
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.Proxy.V1.PhoneNumberContext {}>".format(context)


class PhoneNumberPage(Page):

    def get_instance(self, payload: Dict[str, Any]) -> PhoneNumberInstance:
        """
        Build an instance of PhoneNumberInstance

        :param payload: Payload response from the API
        """
        return PhoneNumberInstance(
            self._version, payload, service_sid=self._solution["service_sid"]
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.Proxy.V1.PhoneNumberPage>"


class PhoneNumberList(ListResource):

    def __init__(self, version: Version, service_sid: str):
        """
        Initialize the PhoneNumberList

        :param version: Version that contains the resource
        :param service_sid: The SID of the parent [Service](https://www.twilio.com/docs/proxy/api/service) of the PhoneNumber resources to read.

        """
        super().__init__(version)

        # Path Solution
        self._solution = {
            "service_sid": service_sid,
        }
        self._uri = "/Services/{service_sid}/PhoneNumbers".format(**self._solution)

    def create(
        self,
        sid: Union[str, object] = values.unset,
        phone_number: Union[str, object] = values.unset,
        is_reserved: Union[bool, object] = values.unset,
    ) -> PhoneNumberInstance:
        """
        Create the PhoneNumberInstance

        :param sid: The SID of a Twilio [IncomingPhoneNumber](https://www.twilio.com/docs/phone-numbers/api/incomingphonenumber-resource) resource that represents the Twilio Number you would like to assign to your Proxy Service.
        :param phone_number: The phone number in [E.164](https://www.twilio.com/docs/glossary/what-e164) format.  E.164 phone numbers consist of a + followed by the country code and subscriber number without punctuation characters. For example, +14155551234.
        :param is_reserved: Whether the new phone number should be reserved and not be assigned to a participant using proxy pool logic. See [Reserved Phone Numbers](https://www.twilio.com/docs/proxy/reserved-phone-numbers) for more information.

        :returns: The created PhoneNumberInstance
        """

        data = values.of(
            {
                "Sid": sid,
                "PhoneNumber": phone_number,
                "IsReserved": serialize.boolean_to_string(is_reserved),
            }
        )
        headers = values.of({"Content-Type": "application/x-www-form-urlencoded"})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = self._version.create(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return PhoneNumberInstance(
            self._version, payload, service_sid=self._solution["service_sid"]
        )

    async def create_async(
        self,
        sid: Union[str, object] = values.unset,
        phone_number: Union[str, object] = values.unset,
        is_reserved: Union[bool, object] = values.unset,
    ) -> PhoneNumberInstance:
        """
        Asynchronously create the PhoneNumberInstance

        :param sid: The SID of a Twilio [IncomingPhoneNumber](https://www.twilio.com/docs/phone-numbers/api/incomingphonenumber-resource) resource that represents the Twilio Number you would like to assign to your Proxy Service.
        :param phone_number: The phone number in [E.164](https://www.twilio.com/docs/glossary/what-e164) format.  E.164 phone numbers consist of a + followed by the country code and subscriber number without punctuation characters. For example, +14155551234.
        :param is_reserved: Whether the new phone number should be reserved and not be assigned to a participant using proxy pool logic. See [Reserved Phone Numbers](https://www.twilio.com/docs/proxy/reserved-phone-numbers) for more information.

        :returns: The created PhoneNumberInstance
        """

        data = values.of(
            {
                "Sid": sid,
                "PhoneNumber": phone_number,
                "IsReserved": serialize.boolean_to_string(is_reserved),
            }
        )
        headers = values.of({"Content-Type": "application/x-www-form-urlencoded"})

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = await self._version.create_async(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return PhoneNumberInstance(
            self._version, payload, service_sid=self._solution["service_sid"]
        )

    def stream(
        self,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Iterator[PhoneNumberInstance]:
        """
        Streams PhoneNumberInstance records from the API as a generator stream.
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
    ) -> AsyncIterator[PhoneNumberInstance]:
        """
        Asynchronously streams PhoneNumberInstance records from the API as a generator stream.
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
    ) -> List[PhoneNumberInstance]:
        """
        Lists PhoneNumberInstance records from the API as a list.
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
    ) -> List[PhoneNumberInstance]:
        """
        Asynchronously lists PhoneNumberInstance records from the API as a list.
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
    ) -> PhoneNumberPage:
        """
        Retrieve a single page of PhoneNumberInstance records from the API.
        Request is executed immediately

        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of PhoneNumberInstance
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
        return PhoneNumberPage(self._version, response, self._solution)

    async def page_async(
        self,
        page_token: Union[str, object] = values.unset,
        page_number: Union[int, object] = values.unset,
        page_size: Union[int, object] = values.unset,
    ) -> PhoneNumberPage:
        """
        Asynchronously retrieve a single page of PhoneNumberInstance records from the API.
        Request is executed immediately

        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of PhoneNumberInstance
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
        return PhoneNumberPage(self._version, response, self._solution)

    def get_page(self, target_url: str) -> PhoneNumberPage:
        """
        Retrieve a specific page of PhoneNumberInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of PhoneNumberInstance
        """
        response = self._version.domain.twilio.request("GET", target_url)
        return PhoneNumberPage(self._version, response, self._solution)

    async def get_page_async(self, target_url: str) -> PhoneNumberPage:
        """
        Asynchronously retrieve a specific page of PhoneNumberInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of PhoneNumberInstance
        """
        response = await self._version.domain.twilio.request_async("GET", target_url)
        return PhoneNumberPage(self._version, response, self._solution)

    def get(self, sid: str) -> PhoneNumberContext:
        """
        Constructs a PhoneNumberContext

        :param sid: The Twilio-provided string that uniquely identifies the PhoneNumber resource to update.
        """
        return PhoneNumberContext(
            self._version, service_sid=self._solution["service_sid"], sid=sid
        )

    def __call__(self, sid: str) -> PhoneNumberContext:
        """
        Constructs a PhoneNumberContext

        :param sid: The Twilio-provided string that uniquely identifies the PhoneNumber resource to update.
        """
        return PhoneNumberContext(
            self._version, service_sid=self._solution["service_sid"], sid=sid
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.Proxy.V1.PhoneNumberList>"
