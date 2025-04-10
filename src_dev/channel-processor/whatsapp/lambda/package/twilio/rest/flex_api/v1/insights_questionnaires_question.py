r"""
    This code was generated by
   ___ _ _ _ _ _    _ ____    ____ ____ _    ____ ____ _  _ ____ ____ ____ ___ __   __
    |  | | | | |    | |  | __ |  | |__| | __ | __ |___ |\ | |___ |__/ |__|  | |  | |__/
    |  |_|_| | |___ | |__|    |__| |  | |    |__] |___ | \| |___ |  \ |  |  | |__| |  \

    Twilio - Flex
    This is the public Twilio REST API.

    NOTE: This class is auto generated by OpenAPI Generator.
    https://openapi-generator.tech
    Do not edit the class manually.
"""

from typing import Any, Dict, List, Optional, Union, Iterator, AsyncIterator
from twilio.base import deserialize, serialize, values
from twilio.base.instance_context import InstanceContext
from twilio.base.instance_resource import InstanceResource
from twilio.base.list_resource import ListResource
from twilio.base.version import Version
from twilio.base.page import Page


class InsightsQuestionnairesQuestionInstance(InstanceResource):
    """
    :ivar account_sid: The SID of the [Account](https://www.twilio.com/docs/iam/api/account) that created the Flex Insights resource and owns this resource.
    :ivar question_sid: The SID of the question
    :ivar question: The question.
    :ivar description: The description for the question.
    :ivar category: The Category for the question.
    :ivar answer_set_id: The answer_set for the question.
    :ivar allow_na: The flag  to enable for disable NA for answer.
    :ivar usage: Integer value that tells a particular question is used by how many questionnaires
    :ivar answer_set: Set of answers for the question
    :ivar url:
    """

    def __init__(
        self,
        version: Version,
        payload: Dict[str, Any],
        question_sid: Optional[str] = None,
    ):
        super().__init__(version)

        self.account_sid: Optional[str] = payload.get("account_sid")
        self.question_sid: Optional[str] = payload.get("question_sid")
        self.question: Optional[str] = payload.get("question")
        self.description: Optional[str] = payload.get("description")
        self.category: Optional[Dict[str, object]] = payload.get("category")
        self.answer_set_id: Optional[str] = payload.get("answer_set_id")
        self.allow_na: Optional[bool] = payload.get("allow_na")
        self.usage: Optional[int] = deserialize.integer(payload.get("usage"))
        self.answer_set: Optional[Dict[str, object]] = payload.get("answer_set")
        self.url: Optional[str] = payload.get("url")

        self._solution = {
            "question_sid": question_sid or self.question_sid,
        }
        self._context: Optional[InsightsQuestionnairesQuestionContext] = None

    @property
    def _proxy(self) -> "InsightsQuestionnairesQuestionContext":
        """
        Generate an instance context for the instance, the context is capable of
        performing various actions. All instance actions are proxied to the context

        :returns: InsightsQuestionnairesQuestionContext for this InsightsQuestionnairesQuestionInstance
        """
        if self._context is None:
            self._context = InsightsQuestionnairesQuestionContext(
                self._version,
                question_sid=self._solution["question_sid"],
            )
        return self._context

    def delete(self, authorization: Union[str, object] = values.unset) -> bool:
        """
        Deletes the InsightsQuestionnairesQuestionInstance

        :param authorization: The Authorization HTTP request header

        :returns: True if delete succeeds, False otherwise
        """
        return self._proxy.delete(
            authorization=authorization,
        )

    async def delete_async(
        self, authorization: Union[str, object] = values.unset
    ) -> bool:
        """
        Asynchronous coroutine that deletes the InsightsQuestionnairesQuestionInstance

        :param authorization: The Authorization HTTP request header

        :returns: True if delete succeeds, False otherwise
        """
        return await self._proxy.delete_async(
            authorization=authorization,
        )

    def update(
        self,
        allow_na: bool,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[str, object] = values.unset,
        question: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        answer_set_id: Union[str, object] = values.unset,
    ) -> "InsightsQuestionnairesQuestionInstance":
        """
        Update the InsightsQuestionnairesQuestionInstance

        :param allow_na: The flag to enable for disable NA for answer.
        :param authorization: The Authorization HTTP request header
        :param category_sid: The SID of the category
        :param question: The question.
        :param description: The description for the question.
        :param answer_set_id: The answer_set for the question.

        :returns: The updated InsightsQuestionnairesQuestionInstance
        """
        return self._proxy.update(
            allow_na=allow_na,
            authorization=authorization,
            category_sid=category_sid,
            question=question,
            description=description,
            answer_set_id=answer_set_id,
        )

    async def update_async(
        self,
        allow_na: bool,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[str, object] = values.unset,
        question: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        answer_set_id: Union[str, object] = values.unset,
    ) -> "InsightsQuestionnairesQuestionInstance":
        """
        Asynchronous coroutine to update the InsightsQuestionnairesQuestionInstance

        :param allow_na: The flag to enable for disable NA for answer.
        :param authorization: The Authorization HTTP request header
        :param category_sid: The SID of the category
        :param question: The question.
        :param description: The description for the question.
        :param answer_set_id: The answer_set for the question.

        :returns: The updated InsightsQuestionnairesQuestionInstance
        """
        return await self._proxy.update_async(
            allow_na=allow_na,
            authorization=authorization,
            category_sid=category_sid,
            question=question,
            description=description,
            answer_set_id=answer_set_id,
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.FlexApi.V1.InsightsQuestionnairesQuestionInstance {}>".format(
            context
        )


class InsightsQuestionnairesQuestionContext(InstanceContext):

    def __init__(self, version: Version, question_sid: str):
        """
        Initialize the InsightsQuestionnairesQuestionContext

        :param version: Version that contains the resource
        :param question_sid: The SID of the question
        """
        super().__init__(version)

        # Path Solution
        self._solution = {
            "question_sid": question_sid,
        }
        self._uri = "/Insights/QualityManagement/Questions/{question_sid}".format(
            **self._solution
        )

    def delete(self, authorization: Union[str, object] = values.unset) -> bool:
        """
        Deletes the InsightsQuestionnairesQuestionInstance

        :param authorization: The Authorization HTTP request header

        :returns: True if delete succeeds, False otherwise
        """
        headers = values.of(
            {
                "Authorization": authorization,
            }
        )

        headers = values.of({})

        return self._version.delete(method="DELETE", uri=self._uri, headers=headers)

    async def delete_async(
        self, authorization: Union[str, object] = values.unset
    ) -> bool:
        """
        Asynchronous coroutine that deletes the InsightsQuestionnairesQuestionInstance

        :param authorization: The Authorization HTTP request header

        :returns: True if delete succeeds, False otherwise
        """
        headers = values.of(
            {
                "Authorization": authorization,
            }
        )

        headers = values.of({})

        return await self._version.delete_async(
            method="DELETE", uri=self._uri, headers=headers
        )

    def update(
        self,
        allow_na: bool,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[str, object] = values.unset,
        question: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        answer_set_id: Union[str, object] = values.unset,
    ) -> InsightsQuestionnairesQuestionInstance:
        """
        Update the InsightsQuestionnairesQuestionInstance

        :param allow_na: The flag to enable for disable NA for answer.
        :param authorization: The Authorization HTTP request header
        :param category_sid: The SID of the category
        :param question: The question.
        :param description: The description for the question.
        :param answer_set_id: The answer_set for the question.

        :returns: The updated InsightsQuestionnairesQuestionInstance
        """

        data = values.of(
            {
                "AllowNa": serialize.boolean_to_string(allow_na),
                "CategorySid": category_sid,
                "Question": question,
                "Description": description,
                "AnswerSetId": answer_set_id,
            }
        )
        headers = values.of({})

        if not (
            authorization is values.unset
            or (isinstance(authorization, str) and not authorization)
        ):
            headers["Authorization"] = authorization

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = self._version.update(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return InsightsQuestionnairesQuestionInstance(
            self._version, payload, question_sid=self._solution["question_sid"]
        )

    async def update_async(
        self,
        allow_na: bool,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[str, object] = values.unset,
        question: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
        answer_set_id: Union[str, object] = values.unset,
    ) -> InsightsQuestionnairesQuestionInstance:
        """
        Asynchronous coroutine to update the InsightsQuestionnairesQuestionInstance

        :param allow_na: The flag to enable for disable NA for answer.
        :param authorization: The Authorization HTTP request header
        :param category_sid: The SID of the category
        :param question: The question.
        :param description: The description for the question.
        :param answer_set_id: The answer_set for the question.

        :returns: The updated InsightsQuestionnairesQuestionInstance
        """

        data = values.of(
            {
                "AllowNa": serialize.boolean_to_string(allow_na),
                "CategorySid": category_sid,
                "Question": question,
                "Description": description,
                "AnswerSetId": answer_set_id,
            }
        )
        headers = values.of({})

        if not (
            authorization is values.unset
            or (isinstance(authorization, str) and not authorization)
        ):
            headers["Authorization"] = authorization

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = await self._version.update_async(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return InsightsQuestionnairesQuestionInstance(
            self._version, payload, question_sid=self._solution["question_sid"]
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        context = " ".join("{}={}".format(k, v) for k, v in self._solution.items())
        return "<Twilio.FlexApi.V1.InsightsQuestionnairesQuestionContext {}>".format(
            context
        )


class InsightsQuestionnairesQuestionPage(Page):

    def get_instance(
        self, payload: Dict[str, Any]
    ) -> InsightsQuestionnairesQuestionInstance:
        """
        Build an instance of InsightsQuestionnairesQuestionInstance

        :param payload: Payload response from the API
        """
        return InsightsQuestionnairesQuestionInstance(self._version, payload)

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.FlexApi.V1.InsightsQuestionnairesQuestionPage>"


class InsightsQuestionnairesQuestionList(ListResource):

    def __init__(self, version: Version):
        """
        Initialize the InsightsQuestionnairesQuestionList

        :param version: Version that contains the resource

        """
        super().__init__(version)

        self._uri = "/Insights/QualityManagement/Questions"

    def create(
        self,
        category_sid: str,
        question: str,
        answer_set_id: str,
        allow_na: bool,
        authorization: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
    ) -> InsightsQuestionnairesQuestionInstance:
        """
        Create the InsightsQuestionnairesQuestionInstance

        :param category_sid: The SID of the category
        :param question: The question.
        :param answer_set_id: The answer_set for the question.
        :param allow_na: The flag to enable for disable NA for answer.
        :param authorization: The Authorization HTTP request header
        :param description: The description for the question.

        :returns: The created InsightsQuestionnairesQuestionInstance
        """

        data = values.of(
            {
                "CategorySid": category_sid,
                "Question": question,
                "AnswerSetId": answer_set_id,
                "AllowNa": serialize.boolean_to_string(allow_na),
                "Description": description,
            }
        )
        headers = values.of(
            {
                "Authorization": authorization,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = self._version.create(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return InsightsQuestionnairesQuestionInstance(self._version, payload)

    async def create_async(
        self,
        category_sid: str,
        question: str,
        answer_set_id: str,
        allow_na: bool,
        authorization: Union[str, object] = values.unset,
        description: Union[str, object] = values.unset,
    ) -> InsightsQuestionnairesQuestionInstance:
        """
        Asynchronously create the InsightsQuestionnairesQuestionInstance

        :param category_sid: The SID of the category
        :param question: The question.
        :param answer_set_id: The answer_set for the question.
        :param allow_na: The flag to enable for disable NA for answer.
        :param authorization: The Authorization HTTP request header
        :param description: The description for the question.

        :returns: The created InsightsQuestionnairesQuestionInstance
        """

        data = values.of(
            {
                "CategorySid": category_sid,
                "Question": question,
                "AnswerSetId": answer_set_id,
                "AllowNa": serialize.boolean_to_string(allow_na),
                "Description": description,
            }
        )
        headers = values.of(
            {
                "Authorization": authorization,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

        headers["Content-Type"] = "application/x-www-form-urlencoded"

        headers["Accept"] = "application/json"

        payload = await self._version.create_async(
            method="POST", uri=self._uri, data=data, headers=headers
        )

        return InsightsQuestionnairesQuestionInstance(self._version, payload)

    def stream(
        self,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[List[str], object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> Iterator[InsightsQuestionnairesQuestionInstance]:
        """
        Streams InsightsQuestionnairesQuestionInstance records from the API as a generator stream.
        This operation lazily loads records as efficiently as possible until the limit
        is reached.
        The results are returned as a generator, so this operation is memory efficient.

        :param str authorization: The Authorization HTTP request header
        :param List[str] category_sid: The list of category SIDs
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
            authorization=authorization,
            category_sid=category_sid,
            page_size=limits["page_size"],
        )

        return self._version.stream(page, limits["limit"])

    async def stream_async(
        self,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[List[str], object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> AsyncIterator[InsightsQuestionnairesQuestionInstance]:
        """
        Asynchronously streams InsightsQuestionnairesQuestionInstance records from the API as a generator stream.
        This operation lazily loads records as efficiently as possible until the limit
        is reached.
        The results are returned as a generator, so this operation is memory efficient.

        :param str authorization: The Authorization HTTP request header
        :param List[str] category_sid: The list of category SIDs
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
            authorization=authorization,
            category_sid=category_sid,
            page_size=limits["page_size"],
        )

        return self._version.stream_async(page, limits["limit"])

    def list(
        self,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[List[str], object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[InsightsQuestionnairesQuestionInstance]:
        """
        Lists InsightsQuestionnairesQuestionInstance records from the API as a list.
        Unlike stream(), this operation is eager and will load `limit` records into
        memory before returning.

        :param str authorization: The Authorization HTTP request header
        :param List[str] category_sid: The list of category SIDs
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
                authorization=authorization,
                category_sid=category_sid,
                limit=limit,
                page_size=page_size,
            )
        )

    async def list_async(
        self,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[List[str], object] = values.unset,
        limit: Optional[int] = None,
        page_size: Optional[int] = None,
    ) -> List[InsightsQuestionnairesQuestionInstance]:
        """
        Asynchronously lists InsightsQuestionnairesQuestionInstance records from the API as a list.
        Unlike stream(), this operation is eager and will load `limit` records into
        memory before returning.

        :param str authorization: The Authorization HTTP request header
        :param List[str] category_sid: The list of category SIDs
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
                authorization=authorization,
                category_sid=category_sid,
                limit=limit,
                page_size=page_size,
            )
        ]

    def page(
        self,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[List[str], object] = values.unset,
        page_token: Union[str, object] = values.unset,
        page_number: Union[int, object] = values.unset,
        page_size: Union[int, object] = values.unset,
    ) -> InsightsQuestionnairesQuestionPage:
        """
        Retrieve a single page of InsightsQuestionnairesQuestionInstance records from the API.
        Request is executed immediately

        :param authorization: The Authorization HTTP request header
        :param category_sid: The list of category SIDs
        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of InsightsQuestionnairesQuestionInstance
        """
        data = values.of(
            {
                "Authorization": authorization,
                "CategorySid": serialize.map(category_sid, lambda e: e),
                "PageToken": page_token,
                "Page": page_number,
                "PageSize": page_size,
            }
        )

        headers = values.of(
            {
                "Authorization": authorization,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

        headers["Accept"] = "application/json"

        response = self._version.page(
            method="GET", uri=self._uri, params=data, headers=headers
        )
        return InsightsQuestionnairesQuestionPage(self._version, response)

    async def page_async(
        self,
        authorization: Union[str, object] = values.unset,
        category_sid: Union[List[str], object] = values.unset,
        page_token: Union[str, object] = values.unset,
        page_number: Union[int, object] = values.unset,
        page_size: Union[int, object] = values.unset,
    ) -> InsightsQuestionnairesQuestionPage:
        """
        Asynchronously retrieve a single page of InsightsQuestionnairesQuestionInstance records from the API.
        Request is executed immediately

        :param authorization: The Authorization HTTP request header
        :param category_sid: The list of category SIDs
        :param page_token: PageToken provided by the API
        :param page_number: Page Number, this value is simply for client state
        :param page_size: Number of records to return, defaults to 50

        :returns: Page of InsightsQuestionnairesQuestionInstance
        """
        data = values.of(
            {
                "Authorization": authorization,
                "CategorySid": serialize.map(category_sid, lambda e: e),
                "PageToken": page_token,
                "Page": page_number,
                "PageSize": page_size,
            }
        )

        headers = values.of(
            {
                "Authorization": authorization,
                "Content-Type": "application/x-www-form-urlencoded",
            }
        )

        headers["Accept"] = "application/json"

        response = await self._version.page_async(
            method="GET", uri=self._uri, params=data, headers=headers
        )
        return InsightsQuestionnairesQuestionPage(self._version, response)

    def get_page(self, target_url: str) -> InsightsQuestionnairesQuestionPage:
        """
        Retrieve a specific page of InsightsQuestionnairesQuestionInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of InsightsQuestionnairesQuestionInstance
        """
        response = self._version.domain.twilio.request("GET", target_url)
        return InsightsQuestionnairesQuestionPage(self._version, response)

    async def get_page_async(
        self, target_url: str
    ) -> InsightsQuestionnairesQuestionPage:
        """
        Asynchronously retrieve a specific page of InsightsQuestionnairesQuestionInstance records from the API.
        Request is executed immediately

        :param target_url: API-generated URL for the requested results page

        :returns: Page of InsightsQuestionnairesQuestionInstance
        """
        response = await self._version.domain.twilio.request_async("GET", target_url)
        return InsightsQuestionnairesQuestionPage(self._version, response)

    def get(self, question_sid: str) -> InsightsQuestionnairesQuestionContext:
        """
        Constructs a InsightsQuestionnairesQuestionContext

        :param question_sid: The SID of the question
        """
        return InsightsQuestionnairesQuestionContext(
            self._version, question_sid=question_sid
        )

    def __call__(self, question_sid: str) -> InsightsQuestionnairesQuestionContext:
        """
        Constructs a InsightsQuestionnairesQuestionContext

        :param question_sid: The SID of the question
        """
        return InsightsQuestionnairesQuestionContext(
            self._version, question_sid=question_sid
        )

    def __repr__(self) -> str:
        """
        Provide a friendly representation

        :returns: Machine friendly representation
        """
        return "<Twilio.FlexApi.V1.InsightsQuestionnairesQuestionList>"
