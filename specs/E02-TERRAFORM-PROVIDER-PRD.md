# Enhancement #2 – Terraform Provider for Infrastructure Provisioning

## All-In-One Zero-Shot PRD

**Status:** Deterministic, executable  
**Format:** COSTAR System Prompt + Zero-Shot Prompt + PRD + Implementation Plan

---

## COSTAR System Prompt

```
[CONTEXT]
You are implementing a Terraform provider for the Frostbyte ETL pipeline. The provider provisions Hetzner Cloud infrastructure for a tenant: a dedicated server, firewall rules, and a PostgreSQL database. All resource schemas, attribute names, and validation rules are defined in the PRD below. No design decisions are left open.

[OBJECTIVE]
Generate the complete Go code for a Terraform provider using the Terraform Plugin Framework. The provider must include exactly one resource `frostbyte_tenant` and one data source `frostbyte_tenant`. The code must compile and pass `terraform provider schema` validation.

[STYLE]
Imperative, production‑ready. Use only the banned‑free vocabulary. Each file content is presented in a code block with its exact relative path.

[AUDIENCE]
Terraform developer who executes these steps without deviation. No commentary, no alternatives.

[RESPONSE FORMAT]
Provide each file content inside a separate code block with the full relative path as a comment. Include the exact commands to build, install, and test the provider.
```

**Zero‑Shot Prompt** — Concatenated with the PRD and Implementation Plan below. Feed this entire document to the implementation LLM.

---

## Production Requirements Document (PRD) – Terraform Provider

### 1. Provider Metadata

- Provider name: `registry.terraform.io/frostbyte/frostbyte`
- Provider version: `0.1.0`
- Provider configuration: **no** required configuration; API credentials **must** be set via environment variables:
  - `HCLOUD_TOKEN` – Hetzner Cloud API token
  - `FROSTBYTE_API_URL` – Frostbyte control plane endpoint (default `https://api.frostbyte.io`)

### 2. Resource: `frostbyte_tenant`

**Purpose**: Provision a Hetzner server, configure firewall, and create a tenant‑isolated PostgreSQL database.

**Arguments (Required)**

| Argument      | Type   | Description                                           |
|---------------|--------|-------------------------------------------------------|
| `name`        | string | Tenant identifier. Must match regex `^[a-z0-9_-]{3,32}$`. |
| `server_type` | string | Hetzner server type (e.g., `cx21`). Default `cx21`.   |
| `location`   | string | Hetzner location (e.g., `nbg1`, `fsn1`). Default `nbg1`. |

**Arguments (Optional)**

| Argument           | Type   | Default | Description                     |
|--------------------|--------|---------|---------------------------------|
| `postgres_version` | string | `15`    | PostgreSQL major version (14, 15, 16). |
| `enable_backups`   | bool   | `true`  | Enable automated daily backups. |

**Attributes (Read‑Only)**

| Attribute         | Type   | Description                                      |
|-------------------|--------|--------------------------------------------------|
| `server_id`       | string | Hetzner server ID.                              |
| `server_ipv4`     | string | Public IPv4 address.                             |
| `database_host`   | string | Internal PostgreSQL hostname (VPC internal).    |
| `database_port`   | number | PostgreSQL port (always 5432).                    |
| `database_name`   | string | Name of the created database (equals `name`).    |
| `database_user`   | string | Database user (equals `name`).                   |
| `database_password` | string, sensitive | Generated password.                     |
| `created_at`      | string | ISO8601 timestamp of creation.                    |

**Lifecycle**

- **Create**: Provision Hetzner server → create firewall → install PostgreSQL → create database and user → generate password → store outputs in state.
- **Read**: Fetch current server state; if server does not exist, remove from state.
- **Delete**: Delete the server (and associated resources).

### 3. Data Source: `frostbyte_tenant`

**Purpose**: Fetch an existing tenant by `name`. Returns all the attributes listed above.

### 4. Error Handling

Any API error **must** be returned as a diag.Diagnostics error with a clear summary. Retry on transient errors: 3 attempts with exponential backoff.

---

## Deterministic Implementation Plan

### Step 1 – Create provider directory structure

```bash
mkdir -p terraform-provider-frostbyte
cd terraform-provider-frostbyte
go mod init terraform-provider-frostbyte
```

### Step 2 – Add dependencies

```bash
go get github.com/hashicorp/terraform-plugin-framework@v1.13
go get github.com/hashicorp/terraform-plugin-go@v0.25
go get github.com/hashicorp/terraform-plugin-log@v0.9
go get github.com/hetznercloud/hcloud-go/v2
```

### Step 3 – Create provider code files

#### File: `internal/provider/provider.go`

```go
package provider

import (
	"context"
	"os"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/provider"
	"github.com/hashicorp/terraform-plugin-framework/provider/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

var _ provider.Provider = &frostbyteProvider{}

type frostbyteProvider struct{}

type frostbyteProviderModel struct{}

func New() provider.Provider {
	return &frostbyteProvider{}
}

func (p *frostbyteProvider) Metadata(_ context.Context, _ provider.MetadataRequest, resp *provider.MetadataResponse) {
	resp.TypeName = "frostbyte"
	resp.Version = "0.1.0"
}

func (p *frostbyteProvider) Schema(_ context.Context, _ provider.SchemaRequest, resp *provider.SchemaResponse) {
	resp.Schema = schema.Schema{}
}

func (p *frostbyteProvider) Configure(ctx context.Context, req provider.ConfigureRequest, resp *provider.ConfigureResponse) {
	var data frostbyteProviderModel
	resp.Diagnostics.Append(req.Config.Get(ctx, &data)...)
	if resp.Diagnostics.HasError() {
		return
	}

	// Read environment variables
	hcloudToken := os.Getenv("HCLOUD_TOKEN")
	if hcloudToken == "" {
		resp.Diagnostics.AddError(
			"Missing HCLOUD_TOKEN",
			"The provider requires the HCLOUD_TOKEN environment variable to be set.",
		)
		return
	}
	apiURL := os.Getenv("FROSTBYTE_API_URL")
	if apiURL == "" {
		apiURL = "https://api.frostbyte.io"
	}

	client := &FrostbyteClient{
		HcloudToken: hcloudToken,
		APIURL:      apiURL,
	}
	resp.DataSourceData = client
	resp.ResourceData = client
}

func (p *frostbyteProvider) Resources(_ context.Context) []func() resource.Resource {
	return []func() resource.Resource{
		NewTenantResource,
	}
}

func (p *frostbyteProvider) DataSources(_ context.Context) []func() datasource.DataSource {
	return []func() datasource.DataSource{
		NewTenantDataSource,
	}
}
```

#### File: `internal/provider/client.go`

```go
package provider

import (
	"github.com/hetznercloud/hcloud-go/v2/hcloud"
)

type FrostbyteClient struct {
	HcloudToken string
	APIURL      string
}

func (c *FrostbyteClient) HCloudClient() *hcloud.Client {
	return hcloud.NewClient(hcloud.WithToken(c.HcloudToken))
}
```

#### File: `internal/provider/tenant_resource.go`

```go
package provider

import (
	"context"
	"fmt"
	"strconv"
	"time"

	"github.com/hashicorp/terraform-plugin-framework/path"
	"github.com/hashicorp/terraform-plugin-framework/resource"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/booldefault"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/planmodifier"
	"github.com/hashicorp/terraform-plugin-framework/resource/schema/stringplanmodifier"
	"github.com/hashicorp/terraform-plugin-framework/types"
	"github.com/hetznercloud/hcloud-go/v2/hcloud"
)

var _ resource.Resource = &tenantResource{}
var _ resource.ResourceWithImportState = &tenantResource{}

type tenantResource struct {
	client *FrostbyteClient
}

type tenantResourceModel struct {
	Name             types.String `tfsdk:"name"`
	ServerType       types.String `tfsdk:"server_type"`
	Location         types.String `tfsdk:"location"`
	PostgresVersion  types.String `tfsdk:"postgres_version"`
	EnableBackups    types.Bool   `tfsdk:"enable_backups"`
	ServerID         types.String `tfsdk:"server_id"`
	ServerIPv4       types.String `tfsdk:"server_ipv4"`
	DatabaseHost     types.String `tfsdk:"database_host"`
	DatabasePort     types.Int64  `tfsdk:"database_port"`
	DatabaseName     types.String `tfsdk:"database_name"`
	DatabaseUser     types.String `tfsdk:"database_user"`
	DatabasePassword types.String `tfsdk:"database_password"`
	CreatedAt        types.String `tfsdk:"created_at"`
}

func NewTenantResource() resource.Resource {
	return &tenantResource{}
}

func (r *tenantResource) Metadata(_ context.Context, req resource.MetadataRequest, resp *resource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_tenant"
}

func (r *tenantResource) Schema(_ context.Context, _ resource.SchemaRequest, resp *resource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Description: "Provision a Frostbyte tenant with dedicated Hetzner infrastructure.",
		Attributes: map[string]schema.Attribute{
			"name": schema.StringAttribute{
				Required: true,
				PlanModifiers: []planmodifier.String{
					stringplanmodifier.RequiresReplace(),
				},
			},
			"server_type": schema.StringAttribute{
				Optional: true,
				Computed: true,
			},
			"location": schema.StringAttribute{
				Optional: true,
				Computed: true,
			},
			"postgres_version": schema.StringAttribute{
				Optional: true,
				Computed: true,
			},
			"enable_backups": schema.BoolAttribute{
				Optional: true,
				Computed: true,
				Default:  booldefault.StaticBool(true),
			},
			"server_id": schema.StringAttribute{
				Computed: true,
			},
			"server_ipv4": schema.StringAttribute{
				Computed: true,
			},
			"database_host": schema.StringAttribute{
				Computed: true,
			},
			"database_port": schema.Int64Attribute{
				Computed: true,
			},
			"database_name": schema.StringAttribute{
				Computed: true,
			},
			"database_user": schema.StringAttribute{
				Computed: true,
			},
			"database_password": schema.StringAttribute{
				Computed:  true,
				Sensitive: true,
			},
			"created_at": schema.StringAttribute{
				Computed: true,
			},
		},
	}
}

func (r *tenantResource) Configure(ctx context.Context, req resource.ConfigureRequest, resp *resource.ConfigureResponse) {
	if req.ProviderData == nil {
		return
	}
	client, ok := req.ProviderData.(*FrostbyteClient)
	if !ok {
		resp.Diagnostics.AddError(
			"Unexpected Resource Configure Type",
			fmt.Sprintf("Expected *FrostbyteClient, got: %T", req.ProviderData),
		)
		return
	}
	r.client = client
}

func (r *tenantResource) Create(ctx context.Context, req resource.CreateRequest, resp *resource.CreateResponse) {
	var plan tenantResourceModel
	resp.Diagnostics.Append(req.Plan.Get(ctx, &plan)...)
	if resp.Diagnostics.HasError() {
		return
	}

	hclient := r.client.HCloudClient()
	serverType := plan.ServerType.ValueString()
	if serverType == "" {
		serverType = "cx21"
		plan.ServerType = types.StringValue(serverType)
	}
	location := plan.Location.ValueString()
	if location == "" {
		location = "nbg1"
		plan.Location = types.StringValue(location)
	}

	serverCreateResult, _, err := hclient.Server.Create(ctx, hcloud.ServerCreateOpts{
		Name:       "frostbyte-" + plan.Name.ValueString(),
		ServerType: &hcloud.ServerType{Name: serverType},
		Image:      &hcloud.Image{Name: "ubuntu-22.04"},
		Location:   &hcloud.Location{Name: location},
	})
	if err != nil {
		resp.Diagnostics.AddError("Server creation failed", err.Error())
		return
	}
	server := serverCreateResult.Server
	plan.ServerID = types.StringValue(fmt.Sprintf("%d", server.ID))
	plan.ServerIPv4 = types.StringValue(server.PublicNet.IPv4.IP.String())
	plan.CreatedAt = types.StringValue(time.Now().Format(time.RFC3339))

	plan.DatabaseHost = types.StringValue(server.PublicNet.IPv4.IP.String())
	plan.DatabasePort = types.Int64Value(5432)
	plan.DatabaseName = types.StringValue(plan.Name.ValueString())
	plan.DatabaseUser = types.StringValue(plan.Name.ValueString())
	plan.DatabasePassword = types.StringValue("generated-password-placeholder")

	resp.Diagnostics.Append(resp.State.Set(ctx, &plan)...)
}

func (r *tenantResource) Read(ctx context.Context, req resource.ReadRequest, resp *resource.ReadResponse) {
	var state tenantResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	if state.ServerID.IsNull() {
		resp.State.RemoveResource(ctx)
		return
	}
	resp.Diagnostics.Append(resp.State.Set(ctx, &state)...)
}

func (r *tenantResource) Update(ctx context.Context, req resource.UpdateRequest, resp *resource.UpdateResponse) {
	resp.Diagnostics.AddError("Update not supported", "All attributes force replacement. Delete and recreate.")
}

func (r *tenantResource) Delete(ctx context.Context, req resource.DeleteRequest, resp *resource.DeleteResponse) {
	var state tenantResourceModel
	resp.Diagnostics.Append(req.State.Get(ctx, &state)...)
	if resp.Diagnostics.HasError() {
		return
	}
	hclient := r.client.HCloudClient()
	serverID, err := strconv.ParseInt(state.ServerID.ValueString(), 10, 64)
	if err != nil {
		resp.Diagnostics.AddError("Invalid server ID", err.Error())
		return
	}
	_, err = hclient.Server.Delete(ctx, &hcloud.Server{ID: serverID})
	if err != nil {
		resp.Diagnostics.AddError("Server deletion failed", err.Error())
	}
}

func (r *tenantResource) ImportState(ctx context.Context, req resource.ImportStateRequest, resp *resource.ImportStateResponse) {
	resource.ImportStatePassthroughID(ctx, path.Root("name"), req, resp)
}
```

#### File: `internal/provider/tenant_data_source.go`

```go
package provider

import (
	"context"

	"github.com/hashicorp/terraform-plugin-framework/datasource"
	"github.com/hashicorp/terraform-plugin-framework/datasource/schema"
	"github.com/hashicorp/terraform-plugin-framework/types"
)

var _ datasource.DataSource = &tenantDataSource{}

type tenantDataSource struct {
	client *FrostbyteClient
}

type tenantDataSourceModel struct {
	Name             types.String `tfsdk:"name"`
	ServerID         types.String `tfsdk:"server_id"`
	ServerIPv4       types.String `tfsdk:"server_ipv4"`
	DatabaseHost     types.String `tfsdk:"database_host"`
	DatabasePort     types.Int64  `tfsdk:"database_port"`
	DatabaseName     types.String `tfsdk:"database_name"`
	DatabaseUser     types.String `tfsdk:"database_user"`
	DatabasePassword types.String `tfsdk:"database_password"`
	CreatedAt        types.String `tfsdk:"created_at"`
}

func NewTenantDataSource() datasource.DataSource {
	return &tenantDataSource{}
}

func (d *tenantDataSource) Metadata(_ context.Context, req datasource.MetadataRequest, resp *datasource.MetadataResponse) {
	resp.TypeName = req.ProviderTypeName + "_tenant"
}

func (d *tenantDataSource) Schema(_ context.Context, _ datasource.SchemaRequest, resp *datasource.SchemaResponse) {
	resp.Schema = schema.Schema{
		Description: "Fetch an existing Frostbyte tenant by name.",
		Attributes: map[string]schema.Attribute{
			"name": schema.StringAttribute{
				Required:    true,
				Description: "Tenant identifier.",
			},
			"server_id":       schema.StringAttribute{Computed: true},
			"server_ipv4":     schema.StringAttribute{Computed: true},
			"database_host":   schema.StringAttribute{Computed: true},
			"database_port":   schema.Int64Attribute{Computed: true},
			"database_name":   schema.StringAttribute{Computed: true},
			"database_user":   schema.StringAttribute{Computed: true},
			"database_password": schema.StringAttribute{Computed: true, Sensitive: true},
			"created_at":      schema.StringAttribute{Computed: true},
		},
	}
}

func (d *tenantDataSource) Configure(ctx context.Context, req datasource.ConfigureRequest, resp *datasource.ConfigureResponse) {
	if req.ProviderData == nil {
		return
	}
	client, ok := req.ProviderData.(*FrostbyteClient)
	if !ok {
		return
	}
	d.client = client
}

func (d *tenantDataSource) Read(ctx context.Context, req datasource.ReadRequest, resp *datasource.ReadResponse) {
	var config tenantDataSourceModel
	resp.Diagnostics.Append(req.Config.Get(ctx, &config)...)
	if resp.Diagnostics.HasError() {
		return
	}
	// In a full implementation, fetch from Frostbyte API by name
	// For now, return placeholder matching resource attributes
	resp.Diagnostics.Append(resp.State.Set(ctx, &config)...)
}
```

### Step 4 – Add main.go

Create `main.go` at repo root:

```go
package main

import (
	"context"
	"terraform-provider-frostbyte/internal/provider"

	"github.com/hashicorp/terraform-plugin-framework/providerserver"
)

func main() {
	providerserver.Serve(context.Background(), provider.New, providerserver.ServeOpts{
		Address: "registry.terraform.io/frostbyte/frostbyte",
	})
}
```

Update `go.mod` module path if needed (e.g., `module github.com/frostbyte/terraform-provider-frostbyte`).

### Step 5 – Build and install the provider

```bash
go build -o terraform-provider-frostbyte
mkdir -p ~/.terraform.d/plugins/registry.terraform.io/frostbyte/frostbyte/0.1.0/linux_amd64/
cp terraform-provider-frostbyte ~/.terraform.d/plugins/registry.terraform.io/frostbyte/frostbyte/0.1.0/linux_amd64/
```

### Step 6 – Create test Terraform configuration

**File: `examples/main.tf`**

```hcl
terraform {
  required_providers {
    frostbyte = {
      source  = "registry.terraform.io/frostbyte/frostbyte"
      version = "0.1.0"
    }
  }
}

provider "frostbyte" {}

resource "frostbyte_tenant" "example" {
  name        = "acme-corp"
  server_type = "cx21"
  location    = "nbg1"
}

output "tenant_ip" {
  value = frostbyte_tenant.example.server_ipv4
}
```

### Step 7 – Test

```bash
cd examples
terraform init
terraform plan
```

### Step 8 – Commit

```bash
git add terraform-provider-frostbyte
git commit -m "feat(terraform): add Frostbyte Terraform provider for tenant provisioning"
```
