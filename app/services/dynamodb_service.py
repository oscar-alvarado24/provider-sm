import os
import uuid
from typing import List, Optional, Dict, Any

import boto3
from botocore.exceptions import ClientError
from boto3.dynamodb.conditions import Attr, Key

from app.models.provider import (
    ProviderCreate,
    ProviderUpdate,
    ProviderResponse,
    ProviderNameResponse,
    Branch,
    BranchCreate
)

class DynamoDBService:
    def __init__(self):
        self.table_name = os.getenv("DYNAMODB_TABLE_NAME", "providers")
        self.aws_region = os.getenv("AWS_REGION_NAME", "us-east-1")
        self.dynamodb_endpoint_url = os.getenv("DYNAMODB_ENDPOINT_URL") # For local development with DynamoDB Local

        if self.dynamodb_endpoint_url:
            self.dynamodb = boto3.resource(
                'dynamodb',
                region_name=self.aws_region,
                endpoint_url=self.dynamodb_endpoint_url
            )
        else:
            self.dynamodb = boto3.resource('dynamodb', region_name=self.aws_region)

        self.table = self.dynamodb.Table(self.table_name)

    def _branch_create_to_dict(self, branch_data: BranchCreate) -> Dict[str, Any]:
        return branch_data.dict()

    def _branches_create_to_list_dict(self, branches: List[BranchCreate]) -> List[Dict[str, Any]]:
        return [self._branch_create_to_dict(branch) for branch in branches]

    def _branch_to_dict(self, branch_data: Branch) -> Dict[str, Any]:
        return branch_data.dict()

    def _branches_to_list_dict(self, branches: List[Branch]) -> List[Dict[str, Any]]:
        return [self._branch_to_dict(branch) for branch in branches]

    def create_provider(self, provider_data: ProviderCreate) -> ProviderResponse:
        provider_id = str(uuid.uuid4())
        item_data = provider_data.dict()
        item_data['id'] = provider_id
        # Ensure branches are stored as list of dicts
        item_data['branches'] = self._branches_create_to_list_dict(provider_data.branches)

        try:
            self.table.put_item(Item=item_data)
            # For the response, we need to convert BranchCreate models within branches to Branch models
            # In this case, Branch and BranchCreate are structurally identical for the response fields
            response_branches = [Branch(**branch.dict()) for branch in provider_data.branches]
            return ProviderResponse(id=provider_id, **provider_data.dict(exclude={'branches'}), branches=response_branches)
        except ClientError as e:
            print(f"Error creating provider in DynamoDB: {e}")
            # Depending on desired error handling, you might re-raise a custom exception
            raise

    def get_provider_by_id(self, provider_id: str) -> Optional[ProviderResponse]:
        try:
            response = self.table.get_item(Key={'id': provider_id})
            item = response.get('Item')
            if item:
                # Ensure branches from DB (list of dicts) are converted to list of Branch models
                item['branches'] = [Branch(**branch_dict) for branch_dict in item.get('branches', [])]
                return ProviderResponse(**item)
            return None
        except ClientError as e:
            print(f"Error getting provider by ID from DynamoDB: {e}")
            raise

    def update_provider(self, provider_id: str, provider_data: ProviderUpdate) -> Optional[ProviderResponse]:
        update_data = provider_data.dict(exclude_unset=True)
        if not update_data:
            # If there's nothing to update, we could return the existing provider or raise an error
            # For now, let's return the existing provider
            return self.get_provider_by_id(provider_id)

        expression_attribute_names = {}
        expression_attribute_values = {}
        update_expression_parts = []

        for key, value in update_data.items():
            placeholder_key = f"#{key}"
            placeholder_value = f":{key}"
            expression_attribute_names[placeholder_key] = key
            if key == "branches" and value is not None:
                 # Convert list of BranchCreate to list of dicts for storage
                expression_attribute_values[placeholder_value] = self._branches_create_to_list_dict(
                    [BranchCreate(**b) for b in value] # Assuming value is list of dicts or BranchCreate models
                )
            else:
                expression_attribute_values[placeholder_value] = value
            update_expression_parts.append(f"{placeholder_key} = {placeholder_value}")

        update_expression = "SET " + ", ".join(update_expression_parts)

        try:
            response = self.table.update_item(
                Key={'id': provider_id},
                UpdateExpression=update_expression,
                ExpressionAttributeNames=expression_attribute_names,
                ExpressionAttributeValues=expression_attribute_values,
                ReturnValues="ALL_NEW" # Gets all attributes of the item after the update
            )
            updated_item = response.get('Attributes')
            if updated_item:
                # Ensure branches from DB (list of dicts) are converted to list of Branch models
                updated_item['branches'] = [Branch(**branch_dict) for branch_dict in updated_item.get('branches', [])]
                return ProviderResponse(**updated_item)
            return None # Should not happen if item exists and update is successful
        except ClientError as e:
            # Handle conditional check failed (e.g., item not found) if needed
            if e.response['Error']['Code'] == 'ConditionalCheckFailedException':
                print(f"Provider with ID {provider_id} not found for update.")
                return None
            print(f"Error updating provider in DynamoDB: {e}")
            raise

    def delete_provider(self, provider_id: str) -> bool:
        try:
            # Check if item exists before deleting for a more informative return
            if self.get_provider_by_id(provider_id) is None:
                return False # Provider not found

            self.table.delete_item(Key={'id': provider_id})
            return True
        except ClientError as e:
            print(f"Error deleting provider from DynamoDB: {e}")
            raise

    def get_providers_by_city_and_service(self, city: str, service: str) -> List[ProviderResponse]:
        # For production, a Global Secondary Index (GSI) on 'address' (or a dedicated 'city' field)
        # and 'services' would be highly recommended for performance instead of a scan.
        # Example GSI: city-services-index (Partition Key: city, Sort Key: services)
        # or a composite GSI if queries are more complex.
        # Scanning can be slow and expensive on large tables.
        items = []
        scan_kwargs = {
            'FilterExpression': Attr('address').contains(city) & Attr('services').contains(service)
        }

        try:
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs['ExclusiveStartKey'] = start_key
                response = self.table.scan(**scan_kwargs)
                items.extend(response.get('Items', []))
                start_key = response.get('LastEvaluatedKey', None)
                done = start_key is None

            providers = []
            for item in items:
                # Ensure branches from DB (list of dicts) are converted to list of Branch models
                item['branches'] = [Branch(**branch_dict) for branch_dict in item.get('branches', [])]
                providers.append(ProviderResponse(**item))
            return providers
        except ClientError as e:
            print(f"Error scanning providers by city and service from DynamoDB: {e}")
            raise

    def get_provider_name_by_id(self, provider_id: str) -> Optional[ProviderNameResponse]:
        try:
            response = self.table.get_item(
                Key={'id': provider_id},
                ProjectionExpression="#id_alias, #name_alias", # Use aliases for attribute names
                ExpressionAttributeNames={
                    "#id_alias": "id", # 'id' is generally safe but good practice
                    "#name_alias": "name" # 'name' can be a reserved keyword
                }
            )
            item = response.get('Item')
            if item:
                # Map aliased keys back to model field names if necessary,
                # but Pydantic should map them if the model fields are 'id' and 'name'
                return ProviderNameResponse(id=item.get('id'), name=item.get('name'))
            return None
        except ClientError as e:
            print(f"Error getting provider name by ID from DynamoDB: {e}")
            raise

# Example usage (for testing locally, not part of the service class itself)
if __name__ == '__main__':
    # Configure for local DynamoDB (ensure DynamoDB local is running)
    os.environ["DYNAMODB_TABLE_NAME"] = "providers-local"
    os.environ["AWS_REGION_NAME"] = "localhost"
    os.environ["DYNAMODB_ENDPOINT_URL"] = "http://localhost:8000"
    # Create table if it doesn't exist (simplified for example)
    try:
        ddb_resource = boto3.resource('dynamodb', endpoint_url=os.environ["DYNAMODB_ENDPOINT_URL"])
        ddb_resource.create_table(
            TableName=os.environ["DYNAMODB_TABLE_NAME"],
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print(f"Table {os.environ['DYNAMODB_TABLE_NAME']} created.")
        # Wait for table to be created
        ddb_resource.meta.client.get_waiter('table_exists').wait(TableName=os.environ["DYNAMODB_TABLE_NAME"])
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"Table {os.environ['DYNAMODB_TABLE_NAME']} already exists.")
        else:
            raise

    service = DynamoDBService()

    # Test create_provider
    print("\n--- Testing Create Provider ---")
    new_provider_data = ProviderCreate(
        name="Test Provider Alpha",
        email="alpha@test.com",
        address="100 Alpha St, Testville, USA",
        phone="555-0100",
        services=["Service A", "Service B"],
        branches=[
            BranchCreate(name="Alpha Branch 1", address="101 Alpha St, Testville", phone="555-0101", manager_name="Manager A1", email="ma1@test.com"),
            BranchCreate(name="Alpha Branch 2", address="102 Alpha St, Testville", phone="555-0102", manager_name="Manager A2", email="ma2@test.com")
        ]
    )
    created_provider = service.create_provider(new_provider_data)
    if created_provider:
        print(f"Created Provider: {created_provider.id} - {created_provider.name}")
        provider_id_to_test = created_provider.id
    else:
        print("Failed to create provider.")
        exit() # Stop if creation fails

    # Test get_provider_by_id
    print("\n--- Testing Get Provider By ID ---")
    provider = service.get_provider_by_id(provider_id_to_test)
    if provider:
        print(f"Got Provider: {provider.name}, Services: {provider.services}, Branches: {[b.name for b in provider.branches]}")
    else:
        print(f"Provider with ID {provider_id_to_test} not found.")

    # Test get_provider_name_by_id
    print("\n--- Testing Get Provider Name By ID ---")
    provider_name_info = service.get_provider_name_by_id(provider_id_to_test)
    if provider_name_info:
        print(f"Got Provider Name Info: {provider_name_info.id} - {provider_name_info.name}")
    else:
        print(f"Provider with ID {provider_id_to_test} not found for name query.")


    # Test update_provider
    print("\n--- Testing Update Provider ---")
    update_payload = ProviderUpdate(
        name="Test Provider Alpha (Updated)",
        services=["Service A", "Service C"], # Updated services
        phone="555-0199"
    )
    updated_provider = service.update_provider(provider_id_to_test, update_payload)
    if updated_provider:
        print(f"Updated Provider: {updated_provider.name}, Services: {updated_provider.services}, Phone: {updated_provider.phone}")
        print(f"Updated Provider Branches: {[b.name for b in updated_provider.branches]}") # Should be original branches
    else:
        print(f"Failed to update provider {provider_id_to_test}.")

    # Test update_provider - updating branches
    print("\n--- Testing Update Provider (Branches) ---")
    update_branches_payload = ProviderUpdate(
        branches=[
            BranchCreate(name="Alpha Branch 1 Remodeled", address="101 Alpha St, Testville", phone="555-0101", manager_name="Manager A1 New", email="ma1new@test.com"),
            BranchCreate(name="Alpha Branch X", address="777 X St, Testville", phone="555-010X", manager_name="Manager AX", email="max@test.com")
        ]
    )
    updated_provider_branches = service.update_provider(provider_id_to_test, update_branches_payload)
    if updated_provider_branches:
        print(f"Updated Provider (Branches): {updated_provider_branches.name}")
        print(f"Branches: {[b.name for b in updated_provider_branches.branches]}")
    else:
        print(f"Failed to update provider branches for {provider_id_to_test}.")


    # Test get_providers_by_city_and_service
    print("\n--- Testing Get Providers by City and Service ---")
    # Create another provider for testing scan
    service.create_provider(ProviderCreate(
        name="Test Provider Beta",
        email="beta@test.com",
        address="200 Beta Ave, Testville, USA", # Same city
        phone="555-0200",
        services=["Service C", "Service D"], # One common service with updated Alpha
        branches=[BranchCreate(name="Beta Branch 1", address="201 Beta Ave", phone="555-0201", manager_name="Manager B1", email="mb1@test.com")]
    ))
    service.create_provider(ProviderCreate(
        name="Test Provider Gamma",
        email="gamma@test.com",
        address="300 Gamma Rd, Otherville, USA", # Different city
        phone="555-0300",
        services=["Service C"],
        branches=[BranchCreate(name="Gamma Branch 1", address="301 Gamma Rd", phone="555-0301", manager_name="Manager G1", email="mg1@test.com")]
    ))

    filtered_providers = service.get_providers_by_city_and_service(city="Testville", service="Service C")
    print(f"Providers in Testville offering Service C: {[p.name for p in filtered_providers]}")
    if "Test Provider Alpha (Updated)" in [p.name for p in filtered_providers] and "Test Provider Beta" in [p.name for p in filtered_providers]:
        print("Scan Test successful for finding relevant providers.")
    else:
        print("Scan Test failed or found unexpected providers.")
        for p in filtered_providers:
            print(f"Found: {p.name} with services {p.services} in address {p.address}")


    # Test delete_provider
    print("\n--- Testing Delete Provider ---")
    delete_status = service.delete_provider(provider_id_to_test)
    print(f"Deletion status for provider {provider_id_to_test}: {delete_status}")
    provider_after_delete = service.get_provider_by_id(provider_id_to_test)
    if provider_after_delete is None:
        print(f"Provider {provider_id_to_test} successfully deleted.")
    else:
        print(f"Provider {provider_id_to_test} still exists after deletion attempt.")

    # Test delete non-existent provider
    print("\n--- Testing Delete Non-existent Provider ---")
    delete_status_non_existent = service.delete_provider("non-existent-id")
    print(f"Deletion status for non-existent provider: {delete_status_non_existent}")
    if not delete_status_non_existent:
        print("Correctly reported non-existent provider for deletion.")
    else:
        print("Incorrectly reported deletion for non-existent provider.")
