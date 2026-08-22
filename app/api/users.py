# app/api/v1/endpoints/users.py
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, HTTPException, Query, Request, status

from app.core.exceptions import AuthenticationError
from app.db.database import DBSession
from app.infrastructure.logging import get_logger
from app.infrastructure.redis.dependencies import (
    ActiveUserRateLimit,
    AdminRateLimit,
    UserRateLimit,
)
from app.schemas.base import PaginatedResponse
from app.schemas.users import (
    PasswordChange,
    UserCreate,
    UserDetailedResponse,
    UserFilters,
    UserResponse,
    UserUpdate,
)
from app.services.users import (
    change_password_by_id,
    delete_user_by_id,
    get_user_by_id,
    get_user_by_username,
    get_users,
    update_user_by_id,
)
from app.services.users import create_user as create_user_service

logger = get_logger(__name__)

router = APIRouter(prefix="/users")


# ===== USER (NON-ADMIN) ENDPOINTS =====


@router.get("/me", response_model=UserDetailedResponse)
async def get_profile(
    user: UserRateLimit,
    db: DBSession,
    request: Request,
):
    """
    Get current user's profile.
    """
    logger.debug(
        "User %s (ID: %s) fetching own profile",
        user.username,
        user.id,
    )

    try:
        user_data = await get_user_by_username(username=user.username, db=db)
    except AuthenticationError as e:
        logger.error(
            "Authentication error fetching profile for user %s: %s",
            user.username,
            str(e),
        )
        logger.user_action(
            action="PROFILE_VIEW",
            username=user.username,
            status="FAILED",
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching profile for user %s: %s",
            user.username,
            str(e),
            exc_info=True,
        )
        logger.user_action(
            action="PROFILE_VIEW",
            username=user.username,
            status="FAILED",
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch profile",
        )

    if user_data is None:
        logger.error(
            "User %s (ID: %s) not found in database",
            user.username,
            user.id,
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User not found",
        )

    # Success logs after validation
    logger.info(
        "User %s (ID: %s) fetched own profile",
        user.username,
        user.id,
    )

    logger.user_action(
        action="PROFILE_VIEW",
        username=user.username,
        request=request,
    )

    return user_data


@router.patch("/me", response_model=UserDetailedResponse)
async def update_profile(
    user: ActiveUserRateLimit,
    new_username: str,
    db: DBSession,
    request: Request,
):
    """
    Update current user's profile.
    """
    logger.debug(
        "User %s (ID: %s) attempting to update username to: %s",
        user.username,
        user.id,
        new_username,
    )

    # Track old username for audit
    old_username = user.username

    try:
        user_data = UserUpdate(username=new_username)
        updated_user = await update_user_by_id(
            user_id=user.id,
            user_data=user_data,
            db=db,
        )
    except AuthenticationError as e:
        logger.error(
            "Authentication error updating profile for user %s: %s",
            user.username,
            str(e),
        )
        logger.user_action(
            action="PROFILE_UPDATE",
            username=user.username,
            status="FAILED",
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ValueError as e:
        logger.error(
            "User %s (ID: %s) failed to update profile: %s",
            user.username,
            user.id,
            str(e),
        )
        logger.user_action(
            action="PROFILE_UPDATE",
            username=user.username,
            status="FAILED",
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error updating profile for user %s: %s",
            user.username,
            str(e),
            exc_info=True,
        )
        logger.user_action(
            action="PROFILE_UPDATE",
            username=user.username,
            status="FAILED",
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update profile",
        )

    # Success logs after try block
    logger.info(
        "User %s (ID: %s) updated username to %s",
        old_username,
        user.id,
        new_username,
    )

    logger.user_action(
        action="PROFILE_UPDATE",
        username=old_username,
        request=request,
        changes={"username": {"from": old_username, "to": new_username}},
    )

    return updated_user


@router.patch("/me/password", response_model=UserResponse)
async def change_own_password(
    user: UserRateLimit,
    password_data: PasswordChange,
    db: DBSession,
    request: Request,
):
    """
    Change current user's own password.
    """
    logger.debug(
        "User %s (ID: %s) attempting to change own password",
        user.username,
        user.id,
    )

    try:
        auth_user = await change_password_by_id(
            user_id=user.id,
            password_data=password_data,
            db=db,
        )
    except AuthenticationError as e:
        logger.error(
            "Authentication error changing password for user %s: %s",
            user.username,
            str(e),
        )
        logger.user_action(
            action="PASSWORD_CHANGE",
            username=user.username,
            status="FAILED",
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ValueError as e:
        logger.error(
            "User %s (ID: %s) failed to change own password: %s",
            user.username,
            user.id,
            str(e),
        )
        logger.user_action(
            action="PASSWORD_CHANGE",
            username=user.username,
            status="FAILED",
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error changing password for user %s: %s",
            user.username,
            str(e),
            exc_info=True,
        )
        logger.user_action(
            action="PASSWORD_CHANGE",
            username=user.username,
            status="FAILED",
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )

    # Success logs after try block
    logger.info(
        "User %s (ID: %s) successfully changed own password",
        user.username,
        user.id,
    )

    logger.user_action(
        action="PASSWORD_CHANGE",
        username=user.username,
        request=request,
    )

    return {"id": auth_user.id, "username": auth_user.username}


# ===== ADMIN ENDPOINTS =====


@router.post("", response_model=UserResponse)
async def create_user(
    user_data: UserCreate, admin: AdminRateLimit, db: DBSession, request: Request
):
    """
    Create a new user (Admin only).
    """
    logger.info(
        "Admin %s (ID: %s) attempting to create user: %s",
        admin.username,
        admin.id,
        user_data.username,
    )

    try:
        result = await create_user_service(
            username=user_data.username,
            password=user_data.password,
            db=db,
            created_by=admin.id,
            must_change_password=True,
            is_active=True,
            role=user_data.role,
        )
    except ValueError as e:
        logger.admin_action(
            action="USER_CREATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user_data.username,
            request=request,
            error=str(e),
        )
        logger.error(
            "Failed to create user %s by admin %s: %s",
            user_data.username,
            admin.username,
            str(e),
        )
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(e))
    except AuthenticationError as e:
        logger.admin_action(
            action="USER_CREATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user_data.username,
            request=request,
            error=str(e),
        )
        logger.error(
            "Authentication error creating user %s by admin %s: %s",
            user_data.username,
            admin.username,
            str(e),
        )
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail=str(e))
    except Exception as e:
        logger.admin_action(
            action="USER_CREATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user_data.username,
            request=request,
            error="Unexpected error",
        )
        logger.error(
            "Unexpected error creating user %s by admin %s: %s",
            user_data.username,
            admin.username,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to create user",
        )

    # Success logs after try block
    logger.info(
        "User %s (ID: %s) created successfully by admin %s (ID: %s)",
        user_data.username,
        result.id,
        admin.username,
        admin.id,
    )

    logger.admin_action(
        action="USER_CREATE",
        admin_id=admin.id,
        admin_username=admin.username,
        target_user=user_data.username,
        target_user_id=result.id,
        changes={"role": user_data.role, "must_change_password": True},
        request=request,
    )

    return result


@router.get("", response_model=PaginatedResponse[UserResponse])
async def get_users_list(
    admin: AdminRateLimit,
    db: DBSession,
    filters: Annotated[UserFilters, Query()],
    request: Request,
):
    """
    Get paginated list of users (Admin only).
    """
    logger.debug(
        "Admin %s (ID: %s) fetching users with filters: %s",
        admin.username,
        admin.id,
        filters.model_dump(exclude_unset=True),
    )

    try:
        users = await get_users(filters=filters, db=db)
    except AuthenticationError as e:
        logger.error(
            "Authentication error fetching users for admin %s: %s",
            admin.username,
            str(e),
        )
        logger.admin_action(
            action="USER_LIST",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ValueError as e:
        logger.error(
            "Admin %s failed to fetch users: %s",
            admin.username,
            str(e),
        )
        logger.admin_action(
            action="USER_LIST",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching users for admin %s: %s",
            admin.username,
            str(e),
            exc_info=True,
        )
        logger.admin_action(
            action="USER_LIST",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch users",
        )

    # Success logs after try block
    logger.info(
        "Admin %s (ID: %s) fetched %d users",
        admin.username,
        admin.id,
        users["total"],
    )

    logger.admin_action(
        action="USER_LIST",
        admin_id=admin.id,
        admin_username=admin.username,
        changes={"filters": filters.model_dump(exclude_unset=True)},
        request=request,
    )

    return users


@router.get("/{user_id}", response_model=UserDetailedResponse)
async def get_user(
    admin: AdminRateLimit,
    user_id: UUID,
    db: DBSession,
    request: Request,
):
    """
    Get user by ID (Admin only).
    """
    logger.debug(
        "Admin %s (ID: %s) fetching user with ID: %s",
        admin.username,
        admin.id,
        user_id,
    )

    try:
        user = await get_user_by_id(user_id=user_id, db=db)
    except AuthenticationError as e:
        logger.warning(
            "Authentication error fetching user %s for admin %s: %s",
            user_id,
            admin.username,
            str(e),
        )
        logger.admin_action(
            action="USER_GET",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching user %s for admin %s: %s",
            user_id,
            admin.username,
            str(e),
            exc_info=True,
        )
        logger.admin_action(
            action="USER_GET",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )

    if user is None:
        logger.warning(
            "Admin %s (ID: %s) attempted to fetch non-existent user ID: %s",
            admin.username,
            admin.id,
            user_id,
        )
        logger.admin_action(
            action="USER_GET",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=f"User with ID {user_id} not found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"there is no user with id= {user_id}",
        )

    # Success logs after validation
    logger.info(
        "Admin %s (ID: %s) fetched user %s (ID: %s)",
        admin.username,
        admin.id,
        user.username,
        user.id,
    )

    logger.admin_action(
        action="USER_GET",
        admin_id=admin.id,
        admin_username=admin.username,
        target_user=user.username,
        target_user_id=user.id,
        request=request,
    )

    return user


@router.patch("/{user_id}", response_model=UserDetailedResponse)
async def update_user(
    admin: AdminRateLimit,
    user_id: UUID,
    user_data: UserUpdate,
    db: DBSession,
    request: Request,
):
    """
    Update user by ID (Admin only).
    """
    logger.debug(
        "Admin %s (ID: %s) attempting to update user ID: %s with data: %s",
        admin.username,
        admin.id,
        user_id,
        user_data.model_dump(exclude_unset=True),
    )

    # Get existing user first to track changes for audit
    try:
        existing_user = await get_user_by_id(user_id=user_id, db=db)
    except AuthenticationError as e:
        logger.warning(
            "Authentication error fetching user %s for update: %s",
            user_id,
            str(e),
        )
        logger.admin_action(
            action="USER_UPDATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching user %s for update: %s",
            user_id,
            str(e),
            exc_info=True,
        )
        logger.admin_action(
            action="USER_UPDATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )

    if existing_user is None:
        logger.warning(
            "Admin %s (ID: %s) attempted to update non-existent user ID: %s",
            admin.username,
            admin.id,
            user_id,
        )
        logger.admin_action(
            action="USER_UPDATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=f"User with ID {user_id} not found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Track changes for audit
    changes = {}
    update_data = user_data.model_dump(exclude_unset=True)

    for field, new_value in update_data.items():
        old_value = getattr(existing_user, field, None)
        if old_value != new_value:
            changes[field] = {"from": old_value, "to": new_value}

    try:
        user = await update_user_by_id(
            user_id=user_id,
            user_data=user_data,
            db=db,
        )
    except AuthenticationError as e:
        logger.admin_action(
            action="USER_UPDATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=existing_user.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        logger.error(
            "Authentication error updating user %s: %s",
            existing_user.username,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ValueError as e:
        logger.admin_action(
            action="USER_UPDATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=existing_user.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        logger.error(
            "Admin %s failed to update user %s: %s",
            admin.username,
            existing_user.username,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.admin_action(
            action="USER_UPDATE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=existing_user.username,
            target_user_id=user_id,
            request=request,
            error="Unexpected error",
        )
        logger.error(
            "Unexpected error updating user %s: %s",
            existing_user.username,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to update user",
        )

    # Success logs after try block
    logger.info(
        "Admin %s (ID: %s) updated user %s (ID: %s)",
        admin.username,
        admin.id,
        user.username,
        user.id,
    )

    if changes:
        logger.admin_action(
            action="USER_UPDATE",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user.username,
            target_user_id=user.id,
            changes=changes,
            request=request,
        )
    else:
        logger.debug("No changes made to user %s", user.username)

    return user


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    admin: AdminRateLimit,
    user_id: UUID,
    db: DBSession,
    request: Request,
):
    """
    Delete user by ID (Admin only).
    """
    logger.debug(
        "Admin %s (ID: %s) attempting to delete user ID: %s",
        admin.username,
        admin.id,
        user_id,
    )

    # Get user info before deletion for audit
    try:
        user_to_delete = await get_user_by_id(user_id=user_id, db=db)
    except AuthenticationError as e:
        logger.warning(
            "Authentication error fetching user %s for deletion: %s",
            user_id,
            str(e),
        )
        logger.admin_action(
            action="USER_DELETE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching user %s for deletion: %s",
            user_id,
            str(e),
            exc_info=True,
        )
        logger.admin_action(
            action="USER_DELETE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )

    if user_to_delete is None:
        logger.warning(
            "Admin %s (ID: %s) attempted to delete non-existent user ID: %s",
            admin.username,
            admin.id,
            user_id,
        )
        logger.admin_action(
            action="USER_DELETE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=f"User with ID {user_id} not found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    # Prevent self-deletion
    if user_id == admin.id:
        logger.warning(
            "Admin %s (ID: %s) attempted to delete themselves",
            admin.username,
            admin.id,
        )
        logger.admin_action(
            action="USER_DELETE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user_to_delete.username,
            target_user_id=user_id,
            request=request,
            error="Self-deletion attempted",
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Cannot delete yourself",
        )

    try:
        await delete_user_by_id(user_id=user_id, db=db)
    except AuthenticationError as e:
        logger.admin_action(
            action="USER_DELETE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user_to_delete.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        logger.error(
            "Authentication error deleting user %s: %s",
            user_to_delete.username,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.admin_action(
            action="USER_DELETE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user_to_delete.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        logger.error(
            "Admin %s failed to delete user %s: %s",
            admin.username,
            user_to_delete.username,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to delete user",
        )

    # Success logs after try block
    logger.info(
        "Admin %s (ID: %s) deleted user %s (ID: %s)",
        admin.username,
        admin.id,
        user_to_delete.username,
        user_id,
    )

    logger.admin_action(
        action="USER_DELETE",
        admin_id=admin.id,
        admin_username=admin.username,
        target_user=user_to_delete.username,
        target_user_id=user_id,
        request=request,
    )


@router.post("/{user_id}/password", response_model=UserResponse)
async def change_password(
    admin: AdminRateLimit,
    user_id: UUID,
    password_data: PasswordChange,
    db: DBSession,
    request: Request,
):
    """
    Change user's password (Admin only).
    """
    logger.debug(
        "Admin %s (ID: %s) attempting to change password for user ID: %s",
        admin.username,
        admin.id,
        user_id,
    )

    # Get user info before password change for audit
    try:
        user = await get_user_by_id(user_id=user_id, db=db)
    except AuthenticationError as e:
        logger.warning(
            "Authentication error fetching user %s for password change: %s",
            user_id,
            str(e),
        )
        logger.admin_action(
            action="USER_PASSWORD_CHANGE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except Exception as e:
        logger.error(
            "Unexpected error fetching user %s for password change: %s",
            user_id,
            str(e),
            exc_info=True,
        )
        logger.admin_action(
            action="USER_PASSWORD_CHANGE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error="Unexpected error",
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to fetch user",
        )

    if user is None:
        logger.warning(
            "Admin %s (ID: %s) attempted to change password for non-existent user ID: %s",
            admin.username,
            admin.id,
            user_id,
        )
        logger.admin_action(
            action="USER_PASSWORD_CHANGE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user_id=user_id,
            request=request,
            error=f"User with ID {user_id} not found",
        )
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"User with ID {user_id} not found",
        )

    try:
        updated_user = await change_password_by_id(
            user_id=user_id,
            password_data=password_data,
            db=db,
        )
    except AuthenticationError as e:
        logger.admin_action(
            action="USER_PASSWORD_CHANGE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        logger.error(
            "Authentication error changing password for user %s: %s",
            user.username,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail=str(e),
        )
    except ValueError as e:
        logger.admin_action(
            action="USER_PASSWORD_CHANGE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user.username,
            target_user_id=user_id,
            request=request,
            error=str(e),
        )
        logger.error(
            "Admin %s failed to change password for user %s: %s",
            admin.username,
            user.username,
            str(e),
        )
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=str(e),
        )
    except Exception as e:
        logger.admin_action(
            action="USER_PASSWORD_CHANGE",
            status="FAILED",
            admin_id=admin.id,
            admin_username=admin.username,
            target_user=user.username,
            target_user_id=user_id,
            request=request,
            error="Unexpected error",
        )
        logger.error(
            "Unexpected error changing password for user %s: %s",
            user.username,
            str(e),
            exc_info=True,
        )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to change password",
        )

    # Success logs after try block
    logger.info(
        "Admin %s (ID: %s) changed password for user %s (ID: %s)",
        admin.username,
        admin.id,
        user.username,
        user_id,
    )

    logger.admin_action(
        action="USER_PASSWORD_CHANGE",
        admin_id=admin.id,
        admin_username=admin.username,
        target_user=user.username,
        target_user_id=user_id,
        request=request,
    )

    return updated_user
