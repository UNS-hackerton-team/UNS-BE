from fastapi import APIRouter, Depends, HTTPException, status

from app.core.deps import get_current_user
from app.core.security import create_access_token
from app.schemas.auth import AuthResponse, LoginRequest, SignupRequest, UserProfile
from app.services.auth import authenticate_user, create_user


router = APIRouter()


@router.post("/signup", response_model=AuthResponse, status_code=status.HTTP_201_CREATED)
async def signup(payload: SignupRequest) -> AuthResponse:
    try:
        user = create_user(payload.name, payload.email, payload.password)
    except ValueError as exc:
        raise HTTPException(
            status_code=status.HTTP_409_CONFLICT,
            detail=str(exc),
        ) from exc

    token = create_access_token(subject=str(user.id))
    return AuthResponse(access_token=token, user=user)


@router.post("/login", response_model=AuthResponse)
async def login(payload: LoginRequest) -> AuthResponse:
    user = authenticate_user(payload.email, payload.password)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid email or password",
        )

    token = create_access_token(subject=str(user.id))
    return AuthResponse(access_token=token, user=user)


@router.get("/me", response_model=UserProfile)
async def me(current_user: dict = Depends(get_current_user)) -> UserProfile:
    return UserProfile(**current_user)
