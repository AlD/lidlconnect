import functools
import gql
from gql.transport.aiohttp import AIOHTTPTransport
import logging
import requests
import textwrap
import time
from typing import Any, Dict, List, Mapping, Optional


class LIDLConnect:

    host = "https://api.lidl-connect.de"

    def __init__(self, username: str, password: str) -> None:
        self.username = username
        self.password = password
        self._tokens = {}

    @property
    def access_token(self) -> str:
        return self.get_token("Bearer")["access_token"]

    @property
    def gql_client(self) -> gql.Client:
        return gql.Client(
            transport=AIOHTTPTransport(
                url=f"{self.host}/api/graphql",
                headers={"Authorization": f"Bearer {self.access_token}"},
            ),
            fetch_schema_from_transport=False,
        )

    def get_token(self, type: str) -> Mapping[str, Any]:
        token = self._tokens.get(type)
        if token and token["expires_at"] > time.time():
            return token
        return self.request_token(type)

    def request_token(self, type: str) -> Mapping[str, Any]:
        match type:
            case "Bearer":
                r = requests.post(
                    f"{self.host}/api/token",
                    data={
                        "grant_type": "password",
                        "client_id": "lidl",
                        "client_secret": "lidl",
                        "username": self.username,
                        "password": self.password,
                    },
                )
                token = r.json()
                token["expires_at"] = time.time() + token["expires_in"]
                self._tokens[type] = token
            case _:
                raise RuntimeError("Unknown token type requested: %s", type)

        return self._tokens[type]

    @property
    def balance(self) -> int:
        response = self.gql(
            query=textwrap.dedent(
                """
                query balanceInfo {
                  currentCustomer {
                    balance
                  }
                }
                """.strip()
            )
        )
        return response["currentCustomer"]["balance"] / 100

    def gql(self, query, operation=None, variables=None) -> Dict[str, Any]:
        gql_args = {"document": gql.gql(query)}
        if operation is not None:
            gql_args["operation_name"] = operation
        if variables is not None:
            gql_args["variable_values"] = variables
        return self.gql_client.execute(**gql_args)

    @functools.cached_property
    def tariffs(self) -> List[Mapping[str, Any]]:
        response = self.gql(
            query=textwrap.dedent(
                """
                query tariffOptions {
                  tariffoptions {
                    bookableTariffoptions {
                      bookableTariffoptions {
                        requiresContractSummary
                        additionalInfo
                        automaticExtension
                        buttonText
                        details
                        formattedPrice
                        name
                        tariffoptionId
                        name
                        price
                        duration {
                          amount
                          unit
                        }
                        notBookableWith
                      }
                    }
                  }
                }
                """.strip()
            )
        )
        return response["tariffoptions"]["bookableTariffoptions"][
            "bookableTariffoptions"
        ]

    def get_tariff(
        self, name: Optional[str] = None, id: Optional[str] = None
    ) -> Mapping[str, Any]:
        for tariff in self.tariffs:
            if tariff["name"] == name or tariff["tariffoptionId"] == id:
                return tariff
        raise RuntimeError("Tariff not found - name: %r, id: %r", name, id)

    @functools.cache
    def resolve_tariff_name(self, name) -> str:
        return self.get_tariff(name=name)["tariffoptionId"]

    @property
    def booked_tariffs(self) -> List[Mapping[str, Any]]:
        response = self.gql(
            query=textwrap.dedent(
                """
                query tariffOptions {
                  tariffoptions {
                    bookedTariffoptions {
                      bookedTariffoptions {
                        automaticExtension
                        tariffoptionId
                        name
                        price
                        duration {
                          amount
                          unit
                        }
                        statusKey
                        startOfRuntime
                        endOfRuntime
                        possibleChangingDate
                        buttonText
                        cancelable
                        formattedPrice
                        restrictedService
                        tariffState
                      }
                    }
                  }
                }
                """.strip()
            )
        )
        return response["tariffoptions"]["bookedTariffoptions"][
            "bookedTariffoptions"
        ]

    def is_booked(self, id) -> bool:
        return any(t["tariffoptionId"] == id for t in self.booked_tariffs)

    @property
    def consumptions(self) -> List[Mapping[str, Any]]:
        response = self.gql(
            query=textwrap.dedent(
                """
                query consumptions {
                  consumptions {
                    consumptionsForUnit {
                      tariffOrOptions {
                        name
                        id
                        type
                        consumptions {
                          consumed
                          unit
                          formattedUnit
                          type
                          description
                          expirationDate
                          left
                          max
                        }
                      }
                    }
                  }
                }
                """
            )
        )["consumptions"]

        tariff_consumptions = []
        for cfu in response["consumptionsForUnit"]:
            if "tariffOrOptions" in cfu:
                tariff_consumptions.extend(cfu["tariffOrOptions"])
        return tariff_consumptions

    def get_consumptions(self, id) -> List[Mapping[str, Any]]:
        return [c for c in self.consumptions if c["id"] == id]

    def book_tariff_option(self, id) -> Mapping[str, Any]:
        response = self.gql(
            operation="tariffOptions",
            variables={"bookTariffoptionInput": {"tariffoptionId": id}},
            query=textwrap.dedent(
                """
                mutation tariffOptions($bookTariffoptionInput: BookTariffoptionInput!) {
                  bookTariffoption(bookTariffoption: $bookTariffoptionInput) {
                    success
                    processId
                    bookTariffoptionDocumentUrl
                  }
                }
                """
            ),
        )["bookTariffoption"]

        if response["success"] != True:
            raise RuntimeError("Unable to book tariff: %r", response)

        return response

    def confirm_tariff_booking(self, pid) -> bool:
        response = self.gql(
            operation="tariffOptions",
            variables={"confirmTariffoptionBookingInput": {"processId": pid}},
            query=textwrap.dedent(
                """
                mutation tariffOptions($confirmTariffoptionBookingInput: ConfirmTariffoptionBookingInput!) {
                  confirmTariffoptionBooking(
                    confirmTariffoptionBooking: $confirmTariffoptionBookingInput
                  ) {
                    success
                  }
                }
                """
            ),
        )["confirmTariffoptionBooking"]

        if response["success"] != True:
            raise RuntimeError("Unable to book tariff: %r", response)

        return True

    def buy_tariff_option(
        self, name: Optional[str] = None, id: Optional[str] = None
    ) -> bool:
        if id is None:
            id = self.resolve_tariff_name(name=name)

        if self.is_booked(id=id):
            logging.info("Tariff %r already booked, checking balance", id)
            left = 0
            max = 0
            for c in self.get_consumptions(id=id):
                for _c in c["consumptions"]:
                    left += _c["left"]
                    max += _c["max"]

            if left > 0:
                logging.info(
                    "Nothing to do, available balance is: %d/%d", left, max
                )
                return True

        pid = self.book_tariff_option(id=id)["processId"]
        return self.confirm_tariff_booking(pid=pid)
