import uuid

from fastapi import APIRouter, Request, Response, status

from app.api.dependencies import ListingServiceDep
from app.schemas import ListingCreate, ListingRead, ListingUpdate

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
def update_listing(
    listing_id: uuid.UUID, data: ListingUpdate, service: ListingServiceDep
):
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