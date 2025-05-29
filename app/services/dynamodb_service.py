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
    def __init__(self, table_name: str, region_name: Optional[str] = None, endpoint_url: Optional[str] = None):
        self.table_name = table_name
        self.region_name = region_name
        self.endpoint_url = endpoint_url

        dynamodb_args = {}
        if self.region_name:
            dynamodb_args['region_name'] = self.region_name
        if self.endpoint_url:
            dynamodb_args['endpoint_url'] = self.endpoint_url
        
        # For local testing with dummy credentials if endpoint_url is set and no real AWS creds are configured
        if self.endpoint_url and not (os.getenv('AWS_ACCESS_KEY_ID') and os.getenv('AWS_SECRET_ACCESS_KEY')):
            if not os.getenv('AWS_SESSION_TOKEN'): # check if not using temp creds from IAM role
                dynamodb_args['aws_access_key_id'] = os.getenv('AWS_ACCESS_KEY_ID', 'dummy')
                dynamodb_args['aws_secret_access_key'] = os.getenv('AWS_SECRET_ACCESS_KEY', 'dummy')

        try:
            # print(f"Initializing DynamoDBService with table: {self.table_name}, region: {self.region_name}, endpoint: {self.endpoint_url}")
            # print(f"Boto3 resource args: {dynamodb_args}")
            self.dynamodb = boto3.resource('dynamodb', **dynamodb_args)
            self.table = self.dynamodb.Table(self.table_name)
            # Optional: Add a check to see if the table actually exists and is accessible
            # self.table.load() 
            # print(f"Successfully connected to table '{self.table_name}'.")
        except ClientError as e:
            # print(f"Error initializing DynamoDB client or table: {e}")
            # Depending on desired behavior, either raise the error or handle it
            # For now, let's re-raise or raise a custom exception
            raise ConnectionError(f"Failed to connect to DynamoDB table '{self.table_name}': {e}")
        except Exception as e: # Catch other potential errors during initialization
            # print(f"An unexpected error occurred during DynamoDBService initialization: {e}")
            raise ConnectionError(f"Unexpected error initializing DynamoDBService: {e}")

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
        """
        Retrieves providers that offer a specific service and have at least one branch in the specified city.
        Service matching is case-sensitive. City matching is case-insensitive.
        Filtering by service is done at the DynamoDB level using Scan's FilterExpression.
        Filtering by city is done on the client-side (Python) due to limitations with querying
        nested objects in a list with DynamoDB Scan filters directly for case-insensitivity.
        A GSI on 'services' (for service filtering) and potentially a composite GSI involving city
        would be more performant in production than a full scan followed by client-side filtering.
        """
        all_scanned_items = []
        # Step 1: Scan DynamoDB for providers offering the specified service.
        scan_kwargs = {
            'FilterExpression': Attr('services').contains(service)
            # Consider adding ProjectionExpression if not all attributes are needed for this operation
        }

        try:
            done = False
            start_key = None
            while not done:
                if start_key:
                    scan_kwargs['ExclusiveStartKey'] = start_key
                response = self.table.scan(**scan_kwargs)
                all_scanned_items.extend(response.get('Items', []))
                start_key = response.get('LastEvaluatedKey', None)
                done = start_key is None
        except ClientError as e:
            print(f"Error scanning providers by service from DynamoDB: {e}")
            raise # Or handle more gracefully

        # Step 2: Client-side filtering for city (case-insensitive) and constructing response.
        results: List[ProviderResponse] = []
        city_lower = city.lower()

        for item in all_scanned_items:
            # The 'service' check is already handled by the Scan FilterExpression.
            # Now, check if any branch is in the specified city.
            has_branch_in_city = False
            if 'branches' in item and isinstance(item['branches'], list):
                for branch_data in item['branches']:
                    # Ensure branch_data is a dict and has a 'city' key
                    if isinstance(branch_data, dict) and branch_data.get('city', '').lower() == city_lower:
                        has_branch_in_city = True
                        break # Found a matching branch, no need to check others for this provider
            
            if has_branch_in_city:
                try:
                    # Convert branch dicts to Branch models
                    # This is crucial for Pydantic validation and correct response structure.
                    branch_models = [Branch(**b_data) for b_data in item.get('branches', [])]
                    # Create a copy of item to avoid modifying the original scanned item dict directly
                    provider_data_for_model = item.copy()
                    provider_data_for_model['branches'] = branch_models
                    
                    results.append(ProviderResponse(**provider_data_for_model))
                except Exception as e: # Catch potential Pydantic validation errors or other issues
                    print(f"Error converting DynamoDB item to ProviderResponse for item ID {item.get('id')}: {e}")
                    # Decide if you want to skip this item or raise an error
                    continue 
        
        return results

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
    local_table_name = "providers-local-filtering-test"
    local_region_name = "localhost" 
    local_endpoint_url = "http://localhost:8000"

    # Create table if it doesn't exist
    try:
        ddb_resource_for_test = boto3.resource(
            'dynamodb',
            endpoint_url=local_endpoint_url,
            region_name=local_region_name,
            aws_access_key_id='dummy',
            aws_secret_access_key='dummy'
        )
        # Delete table if it exists, to ensure clean state for tests
        try:
            table_to_delete = ddb_resource_for_test.Table(local_table_name)
            table_to_delete.delete()
            print(f"Waiting for table {local_table_name} to be deleted...")
            table_to_delete.wait_until_not_exists()
            print(f"Table {local_table_name} deleted.")
        except ClientError as ce:
            if ce.response['Error']['Code'] != 'ResourceNotFoundException':
                print(f"Error deleting existing table {local_table_name}: {ce}")
                # raise # Optional: re-raise if this is critical

        ddb_resource_for_test.create_table(
            TableName=local_table_name,
            KeySchema=[{'AttributeName': 'id', 'KeyType': 'HASH'}],
            AttributeDefinitions=[{'AttributeName': 'id', 'AttributeType': 'S'}],
            ProvisionedThroughput={'ReadCapacityUnits': 5, 'WriteCapacityUnits': 5}
        )
        print(f"Table {local_table_name} creation initiated.")
        ddb_resource_for_test.meta.client.get_waiter('table_exists').wait(TableName=local_table_name)
        print(f"Table {local_table_name} created/confirmed existing.")
    except ClientError as e:
        if e.response['Error']['Code'] == 'ResourceInUseException':
            print(f"Table {local_table_name} already exists (from a parallel creation perhaps, or delete failed).")
        else:
            print(f"Error during table setup for test: {e}")
            exit(1)

    service = DynamoDBService(
        table_name=local_table_name,
        region_name=local_region_name,
        endpoint_url=local_endpoint_url
    )
    print(f"DynamoDBService instantiated for table: {service.table_name}")

    # Test Data
    providers_data = [
        ProviderCreate(
            name="Cloud Pros",
            email="contact@cloudpros.com", address="100 Main St, CloudCity, USA", phone="555-0100",
            services=["Cloud Migration", "Cloud Security", "Consulting"],
            branches=[
                BranchCreate(name="CP North", address="1 N Cloud Ave", city="CloudCity", phone="555-0101", manager_name="Abe N", email="abe@cp.com"),
                BranchCreate(name="CP Metro", address="50 Urban Rd", city="Metroville", phone="555-0102", manager_name="Bea M", email="bea@cp.com")
            ]),
        ProviderCreate(
            name="Data Gurus",
            email="info@datagurus.com", address="200 Data Dr, DataTown, USA", phone="555-0200",
            services=["Data Analytics", "Consulting", "AI Solutions"],
            branches=[
                BranchCreate(name="DG Central", address="10 Central Plaza", city="Metroville", phone="555-0201", manager_name="Cid C", email="cid@dg.com"),
                BranchCreate(name="DG West", address="25 West End", city="Metroville", phone="555-0202", manager_name="Deb W", email="deb@dg.com"),
                BranchCreate(name="DG Oldtown", address="5 Old Mill Rd", city="Oldtown", phone="555-0203", manager_name="Ed O", email="ed@dg.com")
            ]),
        ProviderCreate(
            name="Security Experts Inc.",
            email="secure@secexp.com", address="300 Secure Blvd, SecureCity, USA", phone="555-0300",
            services=["Cloud Security", "Network Security"],
            branches=[
                BranchCreate(name="SE Downtown", address="1 Secure Sq", city="Metroville", phone="555-0301", manager_name="Fae D", email="fae@se.com"),
                BranchCreate(name="SE CloudWatch", address="90 Cloud Ave", city="CloudCity", phone="555-0302", manager_name="Gil C", email="gil@se.com")
            ]),
        ProviderCreate(
            name="Consultants Collective",
            email="contact@cc.com", address="400 Consult Cir, ThinkTank, USA", phone="555-0400",
            services=["Consulting"], # Only consulting
            branches=[
                BranchCreate(name="CC Metro", address="77 Consult St", city="Metroville", phone="555-0401", manager_name="Hal M", email="hal@cc.com")
            ])
    ]
    provider_ids = {}
    print("\n--- Creating Test Providers ---")
    for pd in providers_data:
        created = service.create_provider(pd)
        provider_ids[created.name] = created.id
        print(f"Created: {created.name} (ID: {created.id})")

    # Test Scenarios for get_providers_by_city_and_service
    print("\n--- Testing Get Providers by City and Service ---")

    # Scenario 1: City "Metroville", Service "Consulting"
    # Expected: Cloud Pros, Data Gurus, Consultants Collective
    results1 = service.get_providers_by_city_and_service(city="Metroville", service="Consulting")
    names1 = sorted([p.name for p in results1])
    print(f"Metroville/Consulting: {names1}")
    assert names1 == sorted(["Cloud Pros", "Data Gurus", "Consultants Collective"]), f"FAIL Scenario 1: Expected Cloud Pros, Data Gurus, CC. Got {names1}"
    print("PASS: Metroville/Consulting")

    # Scenario 2: City "CloudCity", Service "Cloud Security"
    # Expected: Cloud Pros, Security Experts Inc.
    results2 = service.get_providers_by_city_and_service(city="CloudCity", service="Cloud Security")
    names2 = sorted([p.name for p in results2])
    print(f"CloudCity/Cloud Security: {names2}")
    assert names2 == sorted(["Cloud Pros", "Security Experts Inc."]), f"FAIL Scenario 2: Expected Cloud Pros, SE Inc. Got {names2}"
    print("PASS: CloudCity/Cloud Security")

    # Scenario 3: City "Oldtown", Service "AI Solutions"
    # Expected: Data Gurus
    results3 = service.get_providers_by_city_and_service(city="Oldtown", service="AI Solutions")
    names3 = sorted([p.name for p in results3])
    print(f"Oldtown/AI Solutions: {names3}")
    assert names3 == ["Data Gurus"], f"FAIL Scenario 3: Expected Data Gurus. Got {names3}"
    print("PASS: Oldtown/AI Solutions")
    
    # Scenario 4: City "Metroville", Service "Data Analytics" (case sensitive service check)
    # Expected: Data Gurus
    results4 = service.get_providers_by_city_and_service(city="metroville", service="Data Analytics") # city case-insensitive
    names4 = sorted([p.name for p in results4])
    print(f"metroville/Data Analytics: {names4}")
    assert names4 == ["Data Gurus"], f"FAIL Scenario 4: Expected Data Gurus. Got {names4}"
    print("PASS: metroville/Data Analytics (case-insensitive city)")

    # Scenario 5: City "NonExistentCity", Service "Consulting"
    # Expected: []
    results5 = service.get_providers_by_city_and_service(city="NonExistentCity", service="Consulting")
    names5 = sorted([p.name for p in results5])
    print(f"NonExistentCity/Consulting: {names5}")
    assert names5 == [], f"FAIL Scenario 5: Expected []. Got {names5}"
    print("PASS: NonExistentCity/Consulting")

    # Scenario 6: City "Metroville", Service "NonExistentService"
    # Expected: []
    results6 = service.get_providers_by_city_and_service(city="Metroville", service="NonExistentService")
    names6 = sorted([p.name for p in results6])
    print(f"Metroville/NonExistentService: {names6}")
    assert names6 == [], f"FAIL Scenario 6: Expected []. Got {names6}"
    print("PASS: Metroville/NonExistentService")
    
    # Scenario 7: Service offered by provider, but no branch in that city
    # Cloud Pros offers "Cloud Migration", but not in "Oldtown"
    results7 = service.get_providers_by_city_and_service(city="Oldtown", service="Cloud Migration")
    names7 = sorted([p.name for p in results7])
    print(f"Oldtown/Cloud Migration: {names7}")
    assert names7 == [], f"FAIL Scenario 7: Expected []. Got {names7}"
    print("PASS: Oldtown/Cloud Migration (service exists, but not in city)")

    print("\n--- All get_providers_by_city_and_service tests passed! ---")

    # Clean up: Delete all created test providers
    print("\n--- Cleaning up test providers ---")
    for name, provider_id in provider_ids.items():
        if service.delete_provider(provider_id):
            print(f"Deleted provider: {name} (ID: {provider_id})")
        else:
            print(f"Failed to delete provider: {name} (ID: {provider_id})")
    
    print("\nLocal tests for DynamoDBService completed.")
