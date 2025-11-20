import pytest
import uuid
from unittest.mock import patch

import importlib.util
from pathlib import Path

# Load booking_tools module from file to avoid importing package `tools.__init__`
booking_tools_path = Path(__file__).resolve().parents[2] / "app" / "v1" / "mcp" / "src" / "tools" / "booking_tools.py"
spec = importlib.util.spec_from_file_location("booking_tools", str(booking_tools_path))
booking_tools = importlib.util.module_from_spec(spec)
spec.loader.exec_module(booking_tools)


class SimpleResult:
	def __init__(self, data=None):
		self.data = data


class FakeTable:
	def __init__(self, name, client):
		self.name = name
		self.client = client
		self._filters = []
		self._insert_data = None
		self._update_data = None
		self._delete = False

	def select(self, *args, **kwargs):
		return self

	def order(self, *args, **kwargs):
		# No-op for ordering in fake client
		return self

	def eq(self, key, value):
		# support multiple filters (multiple .eq() calls)
		self._filters.append((key, value))
		return self

	def execute(self):
		# If previously inserted data exists, return it (simulate insert() -> execute())
		if getattr(self, "_insert_data", None) is not None:
			res = SimpleResult([self._insert_data])
			self._insert_data = None
			return res
		# route by table name
		# If update data is stored and filters exist, apply the update now
		if getattr(self, "_update_data", None) is not None and getattr(self, "_filters", None):
			updates = self._update_data
			# apply for packages
			if self.name == "tour_packages":
				for key, val in self._filters:
					if key == "package_id":
						for p in self.client.packages:
							if p.get("package_id") == val:
								p.update(updates)
								self._update_data = None
								return SimpleResult([p])

			# apply update for bookings
			if self.name == "bookings":
				for key, val in self._filters:
					if key == "booking_id":
						for b in self.client.bookings:
							if b.get("booking_id") == val:
								b.update(updates)
								self._update_data = None
								return SimpleResult([b])

		# if delete flag is set and filters exist, perform deletion
		if getattr(self, "_delete", False) and getattr(self, "_filters", None):
			if self.name == "bookings":
				for key, val in self._filters:
					if key == "booking_id":
						self.client.bookings = [b for b in self.client.bookings if b.get("booking_id") != val]
						self._delete = False
						return SimpleResult([])
		if self.name == "tour_packages":
			# apply filters
			if self._filters:
				results = self.client.packages
				for key, val in self._filters:
					results = [p for p in results if p.get(key) == val]
				return SimpleResult(results)
			return SimpleResult(self.client.packages)

		if self.name == "users":
			if not self._filters:
				return SimpleResult(self.client.users)
			results = self.client.users
			for key, val in self._filters:
				results = [u for u in results if u.get(key) == val]
			return SimpleResult(results)

		if self.name == "bookings":
			if self._filters:
				results = self.client.bookings
				for key, val in self._filters:
					results = [b for b in results if b.get(key) == val]
				return SimpleResult(results)
			return SimpleResult(self.client.bookings)

		return SimpleResult(None)

	def insert(self, data):
		# handle bookings or users
		if self.name == "bookings":
			# generate booking id
			data = data.copy()
			data["booking_id"] = str(uuid.uuid4())
			self.client.bookings.append(data)
			self._insert_data = data
			return self

		if self.name == "users":
			# insert user and return created record
			data = data.copy()
			# generate user_id if not provided
			if not data.get("user_id"):
				data["user_id"] = str(uuid.uuid4())
			self.client.users.append(data)
			self._insert_data = data
			return self

		return self

	def update(self, updates):
		# simplistic: update package slots or booking
		# store update data for later application (eq may follow update)
		self._update_data = updates
		return self

	def delete(self):
		# delete booking
		self._delete = True
		return self


class FakeSupabaseClient:
	def __init__(self):
		self.packages = []
		self.users = []
		self.bookings = []

	def table(self, name):
		return FakeTable(name, self)


@pytest.mark.asyncio
async def test_create_booking_with_existing_user_id():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg1", "available_slots": 10, "price": "1000000", "package_name": "P1", "destination": "A", "start_date": "2025-09-19", "is_active": True}
	fake.packages.append(pkg)
	user = {"user_id": "ansymoer_user4", "full_name": "Test User", "phone_number": "033234242"}
	fake.users.append(user)

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._create_booking_impl(
			user_phone=user["phone_number"],
			package_id=pkg["package_id"],
			number_of_people=3,
			user_id=user["user_id"],
		)

	assert res.get("success") is True
	# last booking should be created with the same user id
	assert fake.bookings
	assert fake.bookings[-1]["user_id"] == user["user_id"]


@pytest.mark.asyncio
async def test_create_booking_with_phone_conflict_uses_existing():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg2", "available_slots": 5, "price": "500000", "package_name": "P2", "destination": "B", "start_date": "2025-10-01", "is_active": True}
	fake.packages.append(pkg)
	existing = {"user_id": "u2", "full_name": "Other User", "phone_number": "033234242"}
	fake.users.append(existing)

	# Provide a different user_id which does not exist
	provided_user_id = "does-not-exist"

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._create_booking_impl(
			user_phone=existing["phone_number"],
			package_id=pkg["package_id"],
			number_of_people=1,
			user_id=provided_user_id,
		)

	assert res.get("success") is True
	assert fake.bookings[-1]["user_id"] == existing["user_id"]


@pytest.mark.asyncio
async def test_delete_booking_removes_record_and_restores_slots():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg3", "available_slots": 2, "price": "200000", "package_name": "P3", "destination": "C", "start_date": "2025-12-01", "is_active": True}
	fake.packages.append(pkg)
	booking = {"booking_id": "b1", "user_id": "u1", "package_id": pkg["package_id"], "number_of_people": 2, "status": "pending"}
	fake.bookings.append(booking)

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._delete_booking_impl(booking_id="b1")

	assert res.get("success") is True
	assert not any(b.get("booking_id") == "b1" for b in fake.bookings)
	# slots restored
	assert fake.packages[0]["available_slots"] == 4


@pytest.mark.asyncio
async def test_get_user_bookings_requires_user_id():
	fake = FakeSupabaseClient()
	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._get_user_bookings_impl(user_id=None)

	assert res.get("success") is False
	assert "missing" in res.get("error", "").lower()


@pytest.mark.asyncio
async def test_create_booking_decrements_slots_and_creates_user_when_needed():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg4", "available_slots": 6, "price": "250000", "package_name": "P4", "destination": "D", "start_date": "2026-01-01", "is_active": True}
	fake.packages.append(pkg)

	# No existing user
	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._create_booking_impl(
			user_phone="0123456789",
			package_id=pkg["package_id"],
			number_of_people=2
		)

	assert res.get("success") is True
	# check user created
	assert len(fake.users) == 1
	# slots decreased
	assert fake.packages[0]["available_slots"] == 4


@pytest.mark.asyncio
async def test_create_booking_insufficient_slots_fails():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg5", "available_slots": 1, "price": "120000", "package_name": "P5", "destination": "E", "start_date": "2026-03-01", "is_active": True}
	fake.packages.append(pkg)

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._create_booking_impl(
			user_phone="0987654321",
			package_id=pkg["package_id"],
			number_of_people=3
		)

	assert res.get("success") is False
	assert "insufficient" in res.get("error", "").lower()


@pytest.mark.asyncio
async def test_get_user_bookings_success_returns_formatted_list():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg6", "available_slots": 10, "price": "300000", "package_name": "P6", "destination": "F", "start_date": "2026-05-01", "is_active": True}
	fake.packages.append(pkg)

	booking = {
		"booking_id": "b2",
		"user_id": "user123",
		"package_id": pkg["package_id"],
		"number_of_people": 2,
		"total_amount": 600000,
		"status": "pending",
		"created_at": "2025-11-20T00:00:00",
		# simulate join
		"tour_packages": {"package_name": pkg["package_name"], "destination": pkg["destination"], "start_date": pkg["start_date"], "price": pkg["price"]}
	}
	fake.bookings.append(booking)

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._get_user_bookings_impl(user_id="user123")

	assert res.get("success") is True
	assert isinstance(res.get("bookings"), list)
	assert len(res.get("bookings")) == 1
	assert res.get("bookings")[0]["tour_name"] == pkg["package_name"]


@pytest.mark.asyncio
async def test_update_booking_increase_people_success_and_slot_check():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg7", "available_slots": 5, "price": "400000", "package_name": "P7", "destination": "G", "start_date": "2026-06-01", "is_active": True}
	fake.packages.append(pkg)
	booking = {"booking_id": "b3", "user_id": "u3", "package_id": pkg["package_id"], "number_of_people": 1, "total_amount": 400000}
	fake.bookings.append(booking)

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._update_booking_impl(booking_id="b3", number_of_people=3)

	assert res.get("success") is True
	# package slots decrease by (3 - 1) = 2
	assert fake.packages[0]["available_slots"] == 3
	assert res.get("booking")["number_of_people"] == 3


@pytest.mark.asyncio
async def test_update_booking_insufficient_slots():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg8", "available_slots": 1, "price": "150000", "package_name": "P8", "destination": "H", "start_date": "2026-07-01", "is_active": True}
	fake.packages.append(pkg)
	booking = {"booking_id": "b4", "user_id": "u4", "package_id": pkg["package_id"], "number_of_people": 1, "total_amount": 150000}
	fake.bookings.append(booking)

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._update_booking_impl(booking_id="b4", number_of_people=5)

	assert res.get("success") is False
	assert "insufficient" in res.get("error", "").lower()


@pytest.mark.asyncio
async def test_delete_booking_fails_if_cancelled():
	fake = FakeSupabaseClient()
	pkg = {"package_id": "pkg9", "available_slots": 2, "price": "180000", "package_name": "P9", "destination": "I", "start_date": "2026-09-01", "is_active": True}
	fake.packages.append(pkg)
	booking = {"booking_id": "b5", "user_id": "u5", "package_id": pkg["package_id"], "number_of_people": 2, "status": "cancelled"}
	fake.bookings.append(booking)

	with patch.object(booking_tools, "get_supabase_client", return_value=fake):
		res = await booking_tools._delete_booking_impl(booking_id="b5")

	assert res.get("success") is False
	assert "already cancelled" in res.get("error", "").lower()

