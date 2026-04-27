# cfn-snowflake-cld.yaml

CloudFormation template that provisions the AWS resources required for a
Snowflake **Catalog-Linked Database (CLD)** backed by AWS Glue Iceberg REST
with Lake Formation vended credentials.

## What the stack creates

| Resource | CFN type | Purpose |
|----------|----------|---------|
| Snowflake SIGV4 IAM role | `AWS::IAM::Role` | Assumed by Snowflake to call the Glue REST API (SigV4) and request LF credentials |
| Lake Formation data-access role | `AWS::IAM::Role` | Assumed by Lake Formation to vend short-lived S3 credentials to Snowflake |
| LF S3 registration | `AWS::LakeFormation::Resource` | Registers the bronze S3 bucket with Lake Formation (hybrid-access mode) |
| Glue DB IAM-only disable | `Custom::GlueDisableIAMOnly` | Clears `CreateTableDefaultPermissions` on the existing Glue database so Lake Formation controls access |
| LF `DESCRIBE` grant on database | `AWS::LakeFormation::PrincipalPermissions` | Allows Snowflake role to see the Glue database during CLD discovery |
| LF `SELECT` + `DESCRIBE` grant on tables | `AWS::LakeFormation::PrincipalPermissions` | Allows Snowflake role to read all tables in the Glue database |

The Glue DB IAM-only disable is handled by an inline Lambda (Python 3.12)
backed by a minimal IAM role (`glue:UpdateDatabase` + CloudWatch Logs).
The Lambda runs on stack create/update and is a no-op on delete.

## Prerequisites

Before deploying this stack:

1. The bronze S3 bucket and Glue database must exist — run `task bronze:glue-setup` and `task bronze:load` first.
2. The Snowflake catalog integration must have been created with `ENABLED = FALSE` so you can extract the trust values (see workflow below).
3. Your AWS credentials must have `CAPABILITY_NAMED_IAM` permissions.

## Deployment workflow

### Step 1 — Create the catalog integration (disabled)

In Snowflake, create the catalog integration but leave it disabled. This lets
Snowflake generate the trust policy values without trying to connect to Glue
before the IAM role exists.

```sql
CREATE OR REPLACE CATALOG INTEGRATION <integration_name>
  CATALOG_SOURCE = ICEBERG_REST
  TABLE_FORMAT = ICEBERG
  CATALOG_NAMESPACE = '<glue_database>'
  REST_CONFIG = (
    CATALOG_URI = 'https://glue.<region>.amazonaws.com/iceberg'
    CATALOG_API_TYPE = AWS_GLUE
  )
  REST_AUTHENTICATION = (
    TYPE = SIGV4
    SIGV4_IAM_ROLE = 'arn:aws:iam::<account_id>:role/<SnowflakeIAMRoleName>'
    SIGV4_SIGNING_REGION = '<region>'
  )
  ACCESS_DELEGATION_MODE = VENDED_CREDENTIALS
  ENABLED = FALSE;
```

### Step 2 — Extract trust values

```sql
DESC CATALOG INTEGRATION <integration_name>;
```

Note these two values from the output:

| Field | Parameter |
|-------|-----------|
| `GLUE_AWS_IAM_USER_ARN` | `SnowflakeUserArn` |
| `GLUE_AWS_EXTERNAL_ID` | `SnowflakeExternalId` |

### Step 3 — Deploy the stack

```bash
aws cloudformation deploy \
  --template-file templates/aws/cfn-snowflake-cld.yaml \
  --stack-name snowflake-cld-iam \
  --capabilities CAPABILITY_NAMED_IAM \
  --region <AWS_REGION> \
  --parameter-overrides \
    SnowflakeExternalId=<GLUE_AWS_EXTERNAL_ID> \
    SnowflakeUserArn=<GLUE_AWS_IAM_USER_ARN> \
    SnowflakeIAMRoleName=<role-name> \
    LFIAMRoleName=<lf-role-name> \
    GlueDatabase=<glue-database-name> \
    S3Bucket=<bronze-bucket-name>
```

Wait 1–2 minutes for IAM to propagate after the stack reaches `CREATE_COMPLETE`.

### Step 4 — Enable the catalog integration

```sql
ALTER CATALOG INTEGRATION <integration_name> SET ENABLED = TRUE;
```

Verify connectivity:

```sql
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('<integration_name>');
-- Expect: {"success": true, ...}
```

### Step 5 — Create the Catalog-Linked Database

```sql
CREATE OR REPLACE DATABASE <cld_database_name>
  LINKED_CATALOG = <integration_name>
  COMMENT = 'Glue Iceberg CLD with vended credentials';
```

## Parameters

All parameters are required — the template has no defaults.

| CFN Parameter | `.env` variable | Description |
|---------------|----------------|-------------|
| `SnowflakeExternalId` | `GLUE_AWS_EXTERNAL_ID` / `API_AWS_EXTERNAL_ID` | External ID from `DESC CATALOG INTEGRATION`. Not in `.env` by default — copy from the DESC output. |
| `SnowflakeUserArn` | `GLUE_AWS_IAM_USER_ARN` / `API_AWS_IAM_USER_ARN` | IAM User ARN from `DESC CATALOG INTEGRATION`. Not in `.env` by default — copy from the DESC output. |
| `SnowflakeIAMRoleName` | `SNOWFLAKE_GLUE_CATALOG_IAM_ROLE_NAME` | Name for the Snowflake SIGV4 IAM role to create. If unset in `.env`, `task snowflake:create-glue-catalog-read-role` derives this from `LAB_USERNAME`. |
| `LFIAMRoleName` | _(no env var)_ | Name for the Lake Formation data-access IAM role to create. Choose a name that does not conflict with existing roles in your account. |
| `GlueDatabase` | `GLUE_DATABASE` | Glue database created by `task bronze:glue-setup`. Defaults to `balloon_pops`; with `LAB_USERNAME` set it becomes `<glue_slug>_balloon_pops`. Run `task bronze:snowflake-summary` to print the resolved value. |
| `S3Bucket` | `BRONZE_BUCKET_NAME` | S3 bucket created by `task bronze:glue-setup`. Run `task bronze:snowflake-summary` to print the resolved value. |

> **Tip:** Run `task bronze:snowflake-summary` to print a copy-paste sheet of the resolved bucket name, Glue database, and ARNs. Run `task snowflake:print-env-hints` to see the resolved catalog integration name (`SNOWFLAKE_CATALOG_INTEGRATION_NAME`, default `glue_rest_catalog_int`) and linked database name.

## Outputs

| Output | Description |
|--------|-------------|
| `SnowflakeRoleArn` | ARN of the Snowflake SIGV4 IAM role — use this in `SIGV4_IAM_ROLE` when creating the catalog integration |
| `LakeFormationRoleArn` | ARN of the Lake Formation data-access role |

Retrieve outputs after deployment:

```bash
aws cloudformation describe-stacks \
  --stack-name snowflake-cld-iam \
  --region <AWS_REGION> \
  --query 'Stacks[0].Outputs'
```

## Cleanup

Delete the stack to remove all IAM roles, LF resource registration, and LF
permissions in one command:

```bash
aws cloudformation delete-stack \
  --stack-name snowflake-cld-iam \
  --region <AWS_REGION>
```

Monitor deletion:

```bash
aws cloudformation wait stack-delete-complete \
  --stack-name snowflake-cld-iam \
  --region <AWS_REGION>
```

> **If deletion fails:** The `AWS::LakeFormation::Resource` registration may
> have active dependencies. Check the CloudFormation **Events** tab for the
> failed resource. You may need to manually deregister the S3 location in
> **Lake Formation → Data lake locations** before retrying the delete.

## Troubleshooting

### "Failed to retrieve credentials from the Catalog" (error code `094120`)

The Lake Formation data lake location is misconfigured. Check:

1. **Data lake location** registered with the LF data-access role (not the service-linked role).
2. **Permission mode** on the S3 location — must be **Hybrid** (set by `HybridAccessEnabled: true` in this template).
3. **Application integration settings** — in **Lake Formation → Administration → Application integration settings**, confirm **"Allow external engines to access data in Amazon S3 locations with full table access"** is enabled. This setting is not managed by this template and must be enabled manually.

After fixing Lake Formation settings, run `CREATE OR REPLACE DATABASE ... LINKED_CATALOG` in
Snowflake — `ALTER DATABASE ... RESUME DISCOVERY` only retries schema/table discovery and will
not re-establish a broken catalog connection.

> **Note:** After `CREATE OR REPLACE DATABASE`, re-run `GRANT USAGE ON INTEGRATION` to restore
> the integration grant.
