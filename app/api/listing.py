import uuid
from typing import Annotated

from fastapi import APIRouter, Query, Request, Response, status

from app.api.dependencies import ListingServiceDep
from app.schemas import (
    ListingCreate,
    ListingQuery,
    ListingRead,
    ListingSearchResult,
    ListingUpdate,
    Page,
)

router = APIRouter(prefix="/listings", tags=["listings"])


@router.post(
    "",
    response_model=ListingRead,
    status_code=status.HTTP_201_CREATED,
    summary="Create a listing",
    responses={422: {"description": "Invalid body, or agent_id does not exist"}},
)
def create_listing(
    data: ListingCreate,
    request: Request,
    response: Response,
    service: ListingServiceDep,
):
    listing = service.create(data)
    response.headers["Location"] = str(
        request.app.url_path_for("get_listing", listing_id=str(listing.id))
    )
    return listing


@router.get(
    "",
    response_model=Page[ListingSearchResult],
    summary="Search and list listings",
    description=(
        "Filter by type, price range and bedrooms. Add latitude, longitude and "
        "radius_km to return only listings within that distance, nearest first "
        "(each result then includes distance_km). Without a location filter, "
        "results are newest first."
    ),
    responses={422: {"description": "Invalid filter or pagination parameters"}},
)
def search_listings(query: Annotated[ListingQuery, Query()], service: ListingServiceDep):
    results, total = service.search(query, limit=query.limit, offset=query.offset)
    return Page[ListingSearchResult](
        items=results, total=total, limit=query.limit, offset=query.offset
    )


@router.get(
    "/{listing_id}",
    response_model=ListingRead,
    summary="Get a listing",
    responses={404: {"description": "Listing not found"}},
)
def get_listing(listing_id: uuid.UUID, service: ListingServiceDep):
    return service.get(listing_id)


@router.patch(
    "/{listing_id}",
    response_model=ListingRead,
    summary="Partially update a listing",
    responses={404: {"description": "Listing not found"}},
)
def update_listing(listing_id: uuid.UUID, data: ListingUpdate, service: ListingServiceDep):
    return service.update(listing_id, data)


@router.delete(
    "/{listing_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    response_class=Response,
    summary="Soft-delete a listing",
    responses={404: {"description": "Listing not found"}},
)
def delete_listing(listing_id: uuid.UUID, service: ListingServiceDep):
    service.delete(listing_id)
