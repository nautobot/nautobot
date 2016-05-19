--
-- PostgreSQL database dump
--

SET statement_timeout = 0;
SET lock_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SET check_function_bodies = false;
SET client_min_messages = warning;

--
-- Name: plpgsql; Type: EXTENSION; Schema: -; Owner: 
--

CREATE EXTENSION IF NOT EXISTS plpgsql WITH SCHEMA pg_catalog;


--
-- Name: EXTENSION plpgsql; Type: COMMENT; Schema: -; Owner: 
--

COMMENT ON EXTENSION plpgsql IS 'PL/pgSQL procedural language';


SET search_path = public, pg_catalog;

SET default_tablespace = '';

SET default_with_oids = false;

--
-- Name: auth_group; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE auth_group (
    id integer NOT NULL,
    name character varying(80) NOT NULL
);


ALTER TABLE public.auth_group OWNER TO django;

--
-- Name: auth_group_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE auth_group_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_id_seq OWNER TO django;

--
-- Name: auth_group_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE auth_group_id_seq OWNED BY auth_group.id;


--
-- Name: auth_group_permissions; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE auth_group_permissions (
    id integer NOT NULL,
    group_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_group_permissions OWNER TO django;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE auth_group_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_group_permissions_id_seq OWNER TO django;

--
-- Name: auth_group_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE auth_group_permissions_id_seq OWNED BY auth_group_permissions.id;


--
-- Name: auth_permission; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE auth_permission (
    id integer NOT NULL,
    name character varying(255) NOT NULL,
    content_type_id integer NOT NULL,
    codename character varying(100) NOT NULL
);


ALTER TABLE public.auth_permission OWNER TO django;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE auth_permission_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_permission_id_seq OWNER TO django;

--
-- Name: auth_permission_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE auth_permission_id_seq OWNED BY auth_permission.id;


--
-- Name: auth_user; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE auth_user (
    id integer NOT NULL,
    password character varying(128) NOT NULL,
    last_login timestamp with time zone,
    is_superuser boolean NOT NULL,
    username character varying(30) NOT NULL,
    first_name character varying(30) NOT NULL,
    last_name character varying(30) NOT NULL,
    email character varying(254) NOT NULL,
    is_staff boolean NOT NULL,
    is_active boolean NOT NULL,
    date_joined timestamp with time zone NOT NULL
);


ALTER TABLE public.auth_user OWNER TO django;

--
-- Name: auth_user_groups; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE auth_user_groups (
    id integer NOT NULL,
    user_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.auth_user_groups OWNER TO django;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE auth_user_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_groups_id_seq OWNER TO django;

--
-- Name: auth_user_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE auth_user_groups_id_seq OWNED BY auth_user_groups.id;


--
-- Name: auth_user_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE auth_user_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_id_seq OWNER TO django;

--
-- Name: auth_user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE auth_user_id_seq OWNED BY auth_user.id;


--
-- Name: auth_user_user_permissions; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE auth_user_user_permissions (
    id integer NOT NULL,
    user_id integer NOT NULL,
    permission_id integer NOT NULL
);


ALTER TABLE public.auth_user_user_permissions OWNER TO django;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE auth_user_user_permissions_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.auth_user_user_permissions_id_seq OWNER TO django;

--
-- Name: auth_user_user_permissions_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE auth_user_user_permissions_id_seq OWNED BY auth_user_user_permissions.id;


--
-- Name: cidr; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE cidr (
    id integer NOT NULL,
    field pg_catalog.cidr NOT NULL
);


ALTER TABLE public.cidr OWNER TO django;

--
-- Name: cidr_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE cidr_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.cidr_id_seq OWNER TO django;

--
-- Name: cidr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE cidr_id_seq OWNED BY cidr.id;


--
-- Name: circuits_circuit; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE circuits_circuit (
    id integer NOT NULL,
    cid character varying(50) NOT NULL,
    install_date date,
    port_speed smallint NOT NULL,
    commit_rate integer,
    comments text NOT NULL,
    interface_id integer,
    provider_id integer NOT NULL,
    site_id integer NOT NULL,
    xconnect_id character varying(50) NOT NULL,
    type_id integer NOT NULL,
    pp_info character varying(100) NOT NULL,
    CONSTRAINT circuits_circuit_commit_rate_check CHECK ((commit_rate >= 0)),
    CONSTRAINT circuits_circuit_port_speed_check CHECK ((port_speed >= 0))
);


ALTER TABLE public.circuits_circuit OWNER TO django;

--
-- Name: circuits_circuit_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE circuits_circuit_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.circuits_circuit_id_seq OWNER TO django;

--
-- Name: circuits_circuit_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE circuits_circuit_id_seq OWNED BY circuits_circuit.id;


--
-- Name: circuits_circuittype; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE circuits_circuittype (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL
);


ALTER TABLE public.circuits_circuittype OWNER TO django;

--
-- Name: circuits_circuittype_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE circuits_circuittype_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.circuits_circuittype_id_seq OWNER TO django;

--
-- Name: circuits_circuittype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE circuits_circuittype_id_seq OWNED BY circuits_circuittype.id;


--
-- Name: circuits_provider; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE circuits_provider (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL,
    asn integer,
    account character varying(30) NOT NULL,
    portal_url character varying(200) NOT NULL,
    noc_contact text NOT NULL,
    admin_contact text NOT NULL,
    comments text NOT NULL,
    CONSTRAINT circuits_provider_asn_check CHECK ((asn >= 0))
);


ALTER TABLE public.circuits_provider OWNER TO django;

--
-- Name: circuits_provider_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE circuits_provider_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.circuits_provider_id_seq OWNER TO django;

--
-- Name: circuits_provider_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE circuits_provider_id_seq OWNED BY circuits_provider.id;


--
-- Name: dcim_consoleport; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_consoleport (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_id integer NOT NULL,
    cs_port_id integer,
    connection_status boolean
);


ALTER TABLE public.dcim_consoleport OWNER TO django;

--
-- Name: dcim_consoleport_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_consoleport_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_consoleport_id_seq OWNER TO django;

--
-- Name: dcim_consoleport_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_consoleport_id_seq OWNED BY dcim_consoleport.id;


--
-- Name: dcim_consoleporttemplate; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_consoleporttemplate (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_type_id integer NOT NULL
);


ALTER TABLE public.dcim_consoleporttemplate OWNER TO django;

--
-- Name: dcim_consoleporttemplate_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_consoleporttemplate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_consoleporttemplate_id_seq OWNER TO django;

--
-- Name: dcim_consoleporttemplate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_consoleporttemplate_id_seq OWNED BY dcim_consoleporttemplate.id;


--
-- Name: dcim_consoleserverport; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_consoleserverport (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_id integer NOT NULL
);


ALTER TABLE public.dcim_consoleserverport OWNER TO django;

--
-- Name: dcim_consoleserverport_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_consoleserverport_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_consoleserverport_id_seq OWNER TO django;

--
-- Name: dcim_consoleserverport_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_consoleserverport_id_seq OWNED BY dcim_consoleserverport.id;


--
-- Name: dcim_consoleserverporttemplate; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_consoleserverporttemplate (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_type_id integer NOT NULL
);


ALTER TABLE public.dcim_consoleserverporttemplate OWNER TO django;

--
-- Name: dcim_consoleserverporttemplate_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_consoleserverporttemplate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_consoleserverporttemplate_id_seq OWNER TO django;

--
-- Name: dcim_consoleserverporttemplate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_consoleserverporttemplate_id_seq OWNED BY dcim_consoleserverporttemplate.id;


--
-- Name: dcim_device; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_device (
    id integer NOT NULL,
    name character varying(50),
    serial character varying(50) NOT NULL,
    "position" smallint,
    face smallint,
    device_type_id integer NOT NULL,
    rack_id integer NOT NULL,
    ro_snmp character varying(50) NOT NULL,
    device_role_id integer NOT NULL,
    primary_ip_id integer,
    status boolean NOT NULL,
    platform_id integer,
    comments text NOT NULL,
    CONSTRAINT dcim_device_face_check CHECK ((face >= 0)),
    CONSTRAINT dcim_device_position_check CHECK (("position" >= 0))
);


ALTER TABLE public.dcim_device OWNER TO django;

--
-- Name: dcim_device_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_device_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_device_id_seq OWNER TO django;

--
-- Name: dcim_device_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_device_id_seq OWNED BY dcim_device.id;


--
-- Name: dcim_devicerole; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_devicerole (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL,
    color character varying(30) NOT NULL
);


ALTER TABLE public.dcim_devicerole OWNER TO django;

--
-- Name: dcim_devicerole_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_devicerole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_devicerole_id_seq OWNER TO django;

--
-- Name: dcim_devicerole_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_devicerole_id_seq OWNED BY dcim_devicerole.id;


--
-- Name: dcim_devicetype; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_devicetype (
    id integer NOT NULL,
    model character varying(50) NOT NULL,
    u_height smallint NOT NULL,
    manufacturer_id integer NOT NULL,
    slug character varying(50) NOT NULL,
    is_console_server boolean NOT NULL,
    is_pdu boolean NOT NULL,
    is_network_device boolean NOT NULL,
    is_full_depth boolean NOT NULL,
    CONSTRAINT dcim_devicetype_u_height_check CHECK ((u_height >= 0))
);


ALTER TABLE public.dcim_devicetype OWNER TO django;

--
-- Name: dcim_devicetype_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_devicetype_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_devicetype_id_seq OWNER TO django;

--
-- Name: dcim_devicetype_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_devicetype_id_seq OWNED BY dcim_devicetype.id;


--
-- Name: dcim_interface; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_interface (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    form_factor smallint NOT NULL,
    mgmt_only boolean NOT NULL,
    device_id integer NOT NULL,
    description character varying(100) NOT NULL,
    CONSTRAINT dcim_interface_form_factor_check CHECK ((form_factor >= 0))
);


ALTER TABLE public.dcim_interface OWNER TO django;

--
-- Name: dcim_interface_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_interface_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_interface_id_seq OWNER TO django;

--
-- Name: dcim_interface_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_interface_id_seq OWNED BY dcim_interface.id;


--
-- Name: dcim_interfaceconnection; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_interfaceconnection (
    id integer NOT NULL,
    interface_a_id integer NOT NULL,
    interface_b_id integer NOT NULL,
    connection_status boolean NOT NULL
);


ALTER TABLE public.dcim_interfaceconnection OWNER TO django;

--
-- Name: dcim_interfaceconnection_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_interfaceconnection_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_interfaceconnection_id_seq OWNER TO django;

--
-- Name: dcim_interfaceconnection_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_interfaceconnection_id_seq OWNED BY dcim_interfaceconnection.id;


--
-- Name: dcim_interfacetemplate; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_interfacetemplate (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    form_factor smallint NOT NULL,
    mgmt_only boolean NOT NULL,
    device_type_id integer NOT NULL,
    CONSTRAINT dcim_interfacetemplate_form_factor_check CHECK ((form_factor >= 0))
);


ALTER TABLE public.dcim_interfacetemplate OWNER TO django;

--
-- Name: dcim_interfacetemplate_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_interfacetemplate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_interfacetemplate_id_seq OWNER TO django;

--
-- Name: dcim_interfacetemplate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_interfacetemplate_id_seq OWNED BY dcim_interfacetemplate.id;


--
-- Name: dcim_manufacturer; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_manufacturer (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL
);


ALTER TABLE public.dcim_manufacturer OWNER TO django;

--
-- Name: dcim_manufacturer_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_manufacturer_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_manufacturer_id_seq OWNER TO django;

--
-- Name: dcim_manufacturer_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_manufacturer_id_seq OWNED BY dcim_manufacturer.id;


--
-- Name: dcim_module; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_module (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    part_id character varying(50) NOT NULL,
    serial character varying(50) NOT NULL,
    device_id integer NOT NULL,
    parent_id integer
);


ALTER TABLE public.dcim_module OWNER TO django;

--
-- Name: dcim_module_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_module_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_module_id_seq OWNER TO django;

--
-- Name: dcim_module_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_module_id_seq OWNED BY dcim_module.id;


--
-- Name: dcim_platform; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_platform (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL,
    rpc_client character varying(30) NOT NULL
);


ALTER TABLE public.dcim_platform OWNER TO django;

--
-- Name: dcim_platform_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_platform_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_platform_id_seq OWNER TO django;

--
-- Name: dcim_platform_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_platform_id_seq OWNED BY dcim_platform.id;


--
-- Name: dcim_poweroutlet; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_poweroutlet (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_id integer NOT NULL
);


ALTER TABLE public.dcim_poweroutlet OWNER TO django;

--
-- Name: dcim_poweroutlet_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_poweroutlet_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_poweroutlet_id_seq OWNER TO django;

--
-- Name: dcim_poweroutlet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_poweroutlet_id_seq OWNED BY dcim_poweroutlet.id;


--
-- Name: dcim_poweroutlettemplate; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_poweroutlettemplate (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_type_id integer NOT NULL
);


ALTER TABLE public.dcim_poweroutlettemplate OWNER TO django;

--
-- Name: dcim_poweroutlettemplate_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_poweroutlettemplate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_poweroutlettemplate_id_seq OWNER TO django;

--
-- Name: dcim_poweroutlettemplate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_poweroutlettemplate_id_seq OWNED BY dcim_poweroutlettemplate.id;


--
-- Name: dcim_powerport; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_powerport (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_id integer NOT NULL,
    power_outlet_id integer,
    connection_status boolean
);


ALTER TABLE public.dcim_powerport OWNER TO django;

--
-- Name: dcim_powerport_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_powerport_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_powerport_id_seq OWNER TO django;

--
-- Name: dcim_powerport_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_powerport_id_seq OWNED BY dcim_powerport.id;


--
-- Name: dcim_powerporttemplate; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_powerporttemplate (
    id integer NOT NULL,
    name character varying(30) NOT NULL,
    device_type_id integer NOT NULL
);


ALTER TABLE public.dcim_powerporttemplate OWNER TO django;

--
-- Name: dcim_powerporttemplate_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_powerporttemplate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_powerporttemplate_id_seq OWNER TO django;

--
-- Name: dcim_powerporttemplate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_powerporttemplate_id_seq OWNED BY dcim_powerporttemplate.id;


--
-- Name: dcim_rack; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_rack (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    facility_id character varying(30),
    u_height smallint NOT NULL,
    site_id integer NOT NULL,
    comments text NOT NULL,
    group_id integer,
    CONSTRAINT dcim_rack_u_height_check CHECK ((u_height >= 0))
);


ALTER TABLE public.dcim_rack OWNER TO django;

--
-- Name: dcim_rack_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_rack_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_rack_id_seq OWNER TO django;

--
-- Name: dcim_rack_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_rack_id_seq OWNED BY dcim_rack.id;


--
-- Name: dcim_rackgroup; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_rackgroup (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL,
    site_id integer NOT NULL
);


ALTER TABLE public.dcim_rackgroup OWNER TO django;

--
-- Name: dcim_rackgroup_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_rackgroup_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_rackgroup_id_seq OWNER TO django;

--
-- Name: dcim_rackgroup_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_rackgroup_id_seq OWNED BY dcim_rackgroup.id;


--
-- Name: dcim_site; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE dcim_site (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL,
    facility character varying(50) NOT NULL,
    asn integer,
    physical_address character varying(200) NOT NULL,
    shipping_address character varying(200) NOT NULL,
    comments text NOT NULL,
    CONSTRAINT dcim_site_asn_check CHECK ((asn >= 0))
);


ALTER TABLE public.dcim_site OWNER TO django;

--
-- Name: dcim_site_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE dcim_site_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.dcim_site_id_seq OWNER TO django;

--
-- Name: dcim_site_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE dcim_site_id_seq OWNED BY dcim_site.id;


--
-- Name: django_admin_log; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE django_admin_log (
    id integer NOT NULL,
    action_time timestamp with time zone NOT NULL,
    object_id text,
    object_repr character varying(200) NOT NULL,
    action_flag smallint NOT NULL,
    change_message text NOT NULL,
    content_type_id integer,
    user_id integer NOT NULL,
    CONSTRAINT django_admin_log_action_flag_check CHECK ((action_flag >= 0))
);


ALTER TABLE public.django_admin_log OWNER TO django;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE django_admin_log_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_admin_log_id_seq OWNER TO django;

--
-- Name: django_admin_log_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE django_admin_log_id_seq OWNED BY django_admin_log.id;


--
-- Name: django_content_type; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE django_content_type (
    id integer NOT NULL,
    app_label character varying(100) NOT NULL,
    model character varying(100) NOT NULL
);


ALTER TABLE public.django_content_type OWNER TO django;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE django_content_type_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_content_type_id_seq OWNER TO django;

--
-- Name: django_content_type_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE django_content_type_id_seq OWNED BY django_content_type.id;


--
-- Name: django_migrations; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE django_migrations (
    id integer NOT NULL,
    app character varying(255) NOT NULL,
    name character varying(255) NOT NULL,
    applied timestamp with time zone NOT NULL
);


ALTER TABLE public.django_migrations OWNER TO django;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE django_migrations_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.django_migrations_id_seq OWNER TO django;

--
-- Name: django_migrations_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE django_migrations_id_seq OWNED BY django_migrations.id;


--
-- Name: django_session; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE django_session (
    session_key character varying(40) NOT NULL,
    session_data text NOT NULL,
    expire_date timestamp with time zone NOT NULL
);


ALTER TABLE public.django_session OWNER TO django;

--
-- Name: extras_exporttemplate; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE extras_exporttemplate (
    id integer NOT NULL,
    name character varying(200) NOT NULL,
    template_code text NOT NULL,
    mime_type character varying(15) NOT NULL,
    file_extension character varying(15) NOT NULL,
    content_type_id integer NOT NULL
);


ALTER TABLE public.extras_exporttemplate OWNER TO django;

--
-- Name: extras_exporttemplate_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE extras_exporttemplate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.extras_exporttemplate_id_seq OWNER TO django;

--
-- Name: extras_exporttemplate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE extras_exporttemplate_id_seq OWNED BY extras_exporttemplate.id;


--
-- Name: extras_graph; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE extras_graph (
    id integer NOT NULL,
    type smallint NOT NULL,
    source character varying(500) NOT NULL,
    link character varying(200) NOT NULL,
    name character varying(100) NOT NULL,
    weight smallint NOT NULL,
    CONSTRAINT extras_graph_type_check CHECK ((type >= 0)),
    CONSTRAINT extras_graph_weight_check CHECK ((weight >= 0))
);


ALTER TABLE public.extras_graph OWNER TO django;

--
-- Name: extras_graph_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE extras_graph_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.extras_graph_id_seq OWNER TO django;

--
-- Name: extras_graph_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE extras_graph_id_seq OWNED BY extras_graph.id;


--
-- Name: extras_topologymap; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE extras_topologymap (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL,
    device_patterns text NOT NULL,
    description character varying(100) NOT NULL,
    site_id integer
);


ALTER TABLE public.extras_topologymap OWNER TO django;

--
-- Name: extras_topologymap_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE extras_topologymap_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.extras_topologymap_id_seq OWNER TO django;

--
-- Name: extras_topologymap_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE extras_topologymap_id_seq OWNED BY extras_topologymap.id;


--
-- Name: inet; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE inet (
    id integer NOT NULL,
    field pg_catalog.inet NOT NULL
);


ALTER TABLE public.inet OWNER TO django;

--
-- Name: inet_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE inet_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.inet_id_seq OWNER TO django;

--
-- Name: inet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE inet_id_seq OWNED BY inet.id;


--
-- Name: ipam_aggregate; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE ipam_aggregate (
    id integer NOT NULL,
    family smallint NOT NULL,
    prefix pg_catalog.cidr NOT NULL,
    rir_id integer NOT NULL,
    date_added date,
    description character varying(100) NOT NULL,
    CONSTRAINT ipam_aggregate_family_check CHECK ((family >= 0))
);


ALTER TABLE public.ipam_aggregate OWNER TO django;

--
-- Name: ipam_aggregate_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE ipam_aggregate_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ipam_aggregate_id_seq OWNER TO django;

--
-- Name: ipam_aggregate_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE ipam_aggregate_id_seq OWNED BY ipam_aggregate.id;


--
-- Name: ipam_ipaddress; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE ipam_ipaddress (
    id integer NOT NULL,
    family smallint NOT NULL,
    address pg_catalog.inet NOT NULL,
    vrf_id integer,
    interface_id integer,
    nat_inside_id integer,
    description character varying(100) NOT NULL,
    CONSTRAINT ipam_ipaddress_family_check CHECK ((family >= 0))
);


ALTER TABLE public.ipam_ipaddress OWNER TO django;

--
-- Name: ipam_ipaddress_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE ipam_ipaddress_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ipam_ipaddress_id_seq OWNER TO django;

--
-- Name: ipam_ipaddress_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE ipam_ipaddress_id_seq OWNED BY ipam_ipaddress.id;


--
-- Name: ipam_prefix; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE ipam_prefix (
    id integer NOT NULL,
    family smallint NOT NULL,
    prefix pg_catalog.cidr NOT NULL,
    vrf_id integer,
    description character varying(100) NOT NULL,
    site_id integer,
    vlan_id integer,
    status smallint NOT NULL,
    role_id integer,
    CONSTRAINT ipam_prefix_family_check CHECK ((family >= 0)),
    CONSTRAINT ipam_prefix_status_4735d2a1_check CHECK ((status >= 0))
);


ALTER TABLE public.ipam_prefix OWNER TO django;

--
-- Name: ipam_prefix_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE ipam_prefix_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ipam_prefix_id_seq OWNER TO django;

--
-- Name: ipam_prefix_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE ipam_prefix_id_seq OWNED BY ipam_prefix.id;


--
-- Name: ipam_rir; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE ipam_rir (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL
);


ALTER TABLE public.ipam_rir OWNER TO django;

--
-- Name: ipam_rir_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE ipam_rir_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ipam_rir_id_seq OWNER TO django;

--
-- Name: ipam_rir_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE ipam_rir_id_seq OWNED BY ipam_rir.id;


--
-- Name: ipam_role; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE ipam_role (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    weight smallint NOT NULL,
    slug character varying(50) NOT NULL,
    CONSTRAINT ipam_role_weight_check CHECK ((weight >= 0))
);


ALTER TABLE public.ipam_role OWNER TO django;

--
-- Name: ipam_role_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE ipam_role_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ipam_role_id_seq OWNER TO django;

--
-- Name: ipam_role_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE ipam_role_id_seq OWNED BY ipam_role.id;


--
-- Name: ipam_vlan; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE ipam_vlan (
    id integer NOT NULL,
    vid smallint NOT NULL,
    name character varying(30) NOT NULL,
    site_id integer NOT NULL,
    status smallint NOT NULL,
    role_id integer,
    CONSTRAINT ipam_vlan_status_77289327_check CHECK ((status >= 0)),
    CONSTRAINT ipam_vlan_vid_check CHECK ((vid >= 0))
);


ALTER TABLE public.ipam_vlan OWNER TO django;

--
-- Name: ipam_vlan_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE ipam_vlan_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ipam_vlan_id_seq OWNER TO django;

--
-- Name: ipam_vlan_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE ipam_vlan_id_seq OWNED BY ipam_vlan.id;


--
-- Name: ipam_vrf; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE ipam_vrf (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    description character varying(100) NOT NULL,
    rd character varying(21) NOT NULL
);


ALTER TABLE public.ipam_vrf OWNER TO django;

--
-- Name: ipam_vrf_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE ipam_vrf_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.ipam_vrf_id_seq OWNER TO django;

--
-- Name: ipam_vrf_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE ipam_vrf_id_seq OWNED BY ipam_vrf.id;


--
-- Name: mac; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE mac (
    id integer NOT NULL,
    field macaddr
);


ALTER TABLE public.mac OWNER TO django;

--
-- Name: mac_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE mac_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.mac_id_seq OWNER TO django;

--
-- Name: mac_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE mac_id_seq OWNED BY mac.id;


--
-- Name: nullcidr; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE nullcidr (
    id integer NOT NULL,
    field pg_catalog.cidr
);


ALTER TABLE public.nullcidr OWNER TO django;

--
-- Name: nullcidr_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE nullcidr_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.nullcidr_id_seq OWNER TO django;

--
-- Name: nullcidr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE nullcidr_id_seq OWNED BY nullcidr.id;


--
-- Name: nullinet; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE nullinet (
    id integer NOT NULL,
    field pg_catalog.inet
);


ALTER TABLE public.nullinet OWNER TO django;

--
-- Name: nullinet_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE nullinet_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.nullinet_id_seq OWNER TO django;

--
-- Name: nullinet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE nullinet_id_seq OWNED BY nullinet.id;


--
-- Name: secrets_secret; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE secrets_secret (
    id integer NOT NULL,
    name character varying(100) NOT NULL,
    ciphertext bytea NOT NULL,
    hash character varying(128) NOT NULL,
    created timestamp with time zone NOT NULL,
    last_modified timestamp with time zone NOT NULL,
    role_id integer NOT NULL,
    device_id integer NOT NULL
);


ALTER TABLE public.secrets_secret OWNER TO django;

--
-- Name: secrets_secret_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE secrets_secret_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.secrets_secret_id_seq OWNER TO django;

--
-- Name: secrets_secret_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE secrets_secret_id_seq OWNED BY secrets_secret.id;


--
-- Name: secrets_secretrole; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE secrets_secretrole (
    id integer NOT NULL,
    name character varying(50) NOT NULL,
    slug character varying(50) NOT NULL
);


ALTER TABLE public.secrets_secretrole OWNER TO django;

--
-- Name: secrets_secretrole_groups; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE secrets_secretrole_groups (
    id integer NOT NULL,
    secretrole_id integer NOT NULL,
    group_id integer NOT NULL
);


ALTER TABLE public.secrets_secretrole_groups OWNER TO django;

--
-- Name: secrets_secretrole_groups_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE secrets_secretrole_groups_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.secrets_secretrole_groups_id_seq OWNER TO django;

--
-- Name: secrets_secretrole_groups_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE secrets_secretrole_groups_id_seq OWNED BY secrets_secretrole_groups.id;


--
-- Name: secrets_secretrole_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE secrets_secretrole_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.secrets_secretrole_id_seq OWNER TO django;

--
-- Name: secrets_secretrole_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE secrets_secretrole_id_seq OWNED BY secrets_secretrole.id;


--
-- Name: secrets_secretrole_users; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE secrets_secretrole_users (
    id integer NOT NULL,
    secretrole_id integer NOT NULL,
    user_id integer NOT NULL
);


ALTER TABLE public.secrets_secretrole_users OWNER TO django;

--
-- Name: secrets_secretrole_users_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE secrets_secretrole_users_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.secrets_secretrole_users_id_seq OWNER TO django;

--
-- Name: secrets_secretrole_users_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE secrets_secretrole_users_id_seq OWNED BY secrets_secretrole_users.id;


--
-- Name: secrets_userkey; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE secrets_userkey (
    id integer NOT NULL,
    public_key text NOT NULL,
    user_id integer NOT NULL,
    created timestamp with time zone NOT NULL,
    master_key_cipher bytea,
    last_modified timestamp with time zone NOT NULL
);


ALTER TABLE public.secrets_userkey OWNER TO django;

--
-- Name: secrets_userkey_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE secrets_userkey_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.secrets_userkey_id_seq OWNER TO django;

--
-- Name: secrets_userkey_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE secrets_userkey_id_seq OWNED BY secrets_userkey.id;


--
-- Name: uniquecidr; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE uniquecidr (
    id integer NOT NULL,
    field pg_catalog.cidr NOT NULL
);


ALTER TABLE public.uniquecidr OWNER TO django;

--
-- Name: uniquecidr_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE uniquecidr_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.uniquecidr_id_seq OWNER TO django;

--
-- Name: uniquecidr_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE uniquecidr_id_seq OWNED BY uniquecidr.id;


--
-- Name: uniqueinet; Type: TABLE; Schema: public; Owner: django; Tablespace: 
--

CREATE TABLE uniqueinet (
    id integer NOT NULL,
    field pg_catalog.inet NOT NULL
);


ALTER TABLE public.uniqueinet OWNER TO django;

--
-- Name: uniqueinet_id_seq; Type: SEQUENCE; Schema: public; Owner: django
--

CREATE SEQUENCE uniqueinet_id_seq
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


ALTER TABLE public.uniqueinet_id_seq OWNER TO django;

--
-- Name: uniqueinet_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: django
--

ALTER SEQUENCE uniqueinet_id_seq OWNED BY uniqueinet.id;


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_group ALTER COLUMN id SET DEFAULT nextval('auth_group_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_group_permissions ALTER COLUMN id SET DEFAULT nextval('auth_group_permissions_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_permission ALTER COLUMN id SET DEFAULT nextval('auth_permission_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_user ALTER COLUMN id SET DEFAULT nextval('auth_user_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_user_groups ALTER COLUMN id SET DEFAULT nextval('auth_user_groups_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_user_user_permissions ALTER COLUMN id SET DEFAULT nextval('auth_user_user_permissions_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY cidr ALTER COLUMN id SET DEFAULT nextval('cidr_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY circuits_circuit ALTER COLUMN id SET DEFAULT nextval('circuits_circuit_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY circuits_circuittype ALTER COLUMN id SET DEFAULT nextval('circuits_circuittype_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY circuits_provider ALTER COLUMN id SET DEFAULT nextval('circuits_provider_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleport ALTER COLUMN id SET DEFAULT nextval('dcim_consoleport_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleporttemplate ALTER COLUMN id SET DEFAULT nextval('dcim_consoleporttemplate_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleserverport ALTER COLUMN id SET DEFAULT nextval('dcim_consoleserverport_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleserverporttemplate ALTER COLUMN id SET DEFAULT nextval('dcim_consoleserverporttemplate_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_device ALTER COLUMN id SET DEFAULT nextval('dcim_device_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_devicerole ALTER COLUMN id SET DEFAULT nextval('dcim_devicerole_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_devicetype ALTER COLUMN id SET DEFAULT nextval('dcim_devicetype_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_interface ALTER COLUMN id SET DEFAULT nextval('dcim_interface_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_interfaceconnection ALTER COLUMN id SET DEFAULT nextval('dcim_interfaceconnection_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_interfacetemplate ALTER COLUMN id SET DEFAULT nextval('dcim_interfacetemplate_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_manufacturer ALTER COLUMN id SET DEFAULT nextval('dcim_manufacturer_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_module ALTER COLUMN id SET DEFAULT nextval('dcim_module_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_platform ALTER COLUMN id SET DEFAULT nextval('dcim_platform_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_poweroutlet ALTER COLUMN id SET DEFAULT nextval('dcim_poweroutlet_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_poweroutlettemplate ALTER COLUMN id SET DEFAULT nextval('dcim_poweroutlettemplate_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_powerport ALTER COLUMN id SET DEFAULT nextval('dcim_powerport_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_powerporttemplate ALTER COLUMN id SET DEFAULT nextval('dcim_powerporttemplate_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_rack ALTER COLUMN id SET DEFAULT nextval('dcim_rack_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_rackgroup ALTER COLUMN id SET DEFAULT nextval('dcim_rackgroup_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_site ALTER COLUMN id SET DEFAULT nextval('dcim_site_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY django_admin_log ALTER COLUMN id SET DEFAULT nextval('django_admin_log_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY django_content_type ALTER COLUMN id SET DEFAULT nextval('django_content_type_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY django_migrations ALTER COLUMN id SET DEFAULT nextval('django_migrations_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY extras_exporttemplate ALTER COLUMN id SET DEFAULT nextval('extras_exporttemplate_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY extras_graph ALTER COLUMN id SET DEFAULT nextval('extras_graph_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY extras_topologymap ALTER COLUMN id SET DEFAULT nextval('extras_topologymap_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY inet ALTER COLUMN id SET DEFAULT nextval('inet_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_aggregate ALTER COLUMN id SET DEFAULT nextval('ipam_aggregate_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_ipaddress ALTER COLUMN id SET DEFAULT nextval('ipam_ipaddress_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_prefix ALTER COLUMN id SET DEFAULT nextval('ipam_prefix_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_rir ALTER COLUMN id SET DEFAULT nextval('ipam_rir_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_role ALTER COLUMN id SET DEFAULT nextval('ipam_role_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_vlan ALTER COLUMN id SET DEFAULT nextval('ipam_vlan_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_vrf ALTER COLUMN id SET DEFAULT nextval('ipam_vrf_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY mac ALTER COLUMN id SET DEFAULT nextval('mac_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY nullcidr ALTER COLUMN id SET DEFAULT nextval('nullcidr_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY nullinet ALTER COLUMN id SET DEFAULT nextval('nullinet_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secret ALTER COLUMN id SET DEFAULT nextval('secrets_secret_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secretrole ALTER COLUMN id SET DEFAULT nextval('secrets_secretrole_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secretrole_groups ALTER COLUMN id SET DEFAULT nextval('secrets_secretrole_groups_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secretrole_users ALTER COLUMN id SET DEFAULT nextval('secrets_secretrole_users_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_userkey ALTER COLUMN id SET DEFAULT nextval('secrets_userkey_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY uniquecidr ALTER COLUMN id SET DEFAULT nextval('uniquecidr_id_seq'::regclass);


--
-- Name: id; Type: DEFAULT; Schema: public; Owner: django
--

ALTER TABLE ONLY uniqueinet ALTER COLUMN id SET DEFAULT nextval('uniqueinet_id_seq'::regclass);


--
-- Name: auth_group_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_group
    ADD CONSTRAINT auth_group_name_key UNIQUE (name);


--
-- Name: auth_group_permissions_group_id_permission_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_group_id_permission_id_key UNIQUE (group_id, permission_id);


--
-- Name: auth_group_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_group_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_group
    ADD CONSTRAINT auth_group_pkey PRIMARY KEY (id);


--
-- Name: auth_permission_content_type_id_codename_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_content_type_id_codename_key UNIQUE (content_type_id, codename);


--
-- Name: auth_permission_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_permission_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_user_groups
    ADD CONSTRAINT auth_user_groups_pkey PRIMARY KEY (id);


--
-- Name: auth_user_groups_user_id_group_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_group_id_key UNIQUE (user_id, group_id);


--
-- Name: auth_user_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_user
    ADD CONSTRAINT auth_user_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_pkey PRIMARY KEY (id);


--
-- Name: auth_user_user_permissions_user_id_permission_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permissions_user_id_permission_id_key UNIQUE (user_id, permission_id);


--
-- Name: auth_user_username_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY auth_user
    ADD CONSTRAINT auth_user_username_key UNIQUE (username);


--
-- Name: cidr_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY cidr
    ADD CONSTRAINT cidr_pkey PRIMARY KEY (id);


--
-- Name: circuits_circuit_interface_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_circuit
    ADD CONSTRAINT circuits_circuit_interface_id_key UNIQUE (interface_id);


--
-- Name: circuits_circuit_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_circuit
    ADD CONSTRAINT circuits_circuit_pkey PRIMARY KEY (id);


--
-- Name: circuits_circuit_provider_id_4eab740723ebc621_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_circuit
    ADD CONSTRAINT circuits_circuit_provider_id_4eab740723ebc621_uniq UNIQUE (provider_id, cid);


--
-- Name: circuits_circuittype_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_circuittype
    ADD CONSTRAINT circuits_circuittype_name_key UNIQUE (name);


--
-- Name: circuits_circuittype_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_circuittype
    ADD CONSTRAINT circuits_circuittype_pkey PRIMARY KEY (id);


--
-- Name: circuits_circuittype_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_circuittype
    ADD CONSTRAINT circuits_circuittype_slug_key UNIQUE (slug);


--
-- Name: circuits_provider_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_provider
    ADD CONSTRAINT circuits_provider_name_key UNIQUE (name);


--
-- Name: circuits_provider_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_provider
    ADD CONSTRAINT circuits_provider_pkey PRIMARY KEY (id);


--
-- Name: circuits_provider_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY circuits_provider
    ADD CONSTRAINT circuits_provider_slug_key UNIQUE (slug);


--
-- Name: dcim_consoleport_cs_port_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleport
    ADD CONSTRAINT dcim_consoleport_cs_port_id_key UNIQUE (cs_port_id);


--
-- Name: dcim_consoleport_device_id_2bfdd4b8ce9af21e_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleport
    ADD CONSTRAINT dcim_consoleport_device_id_2bfdd4b8ce9af21e_uniq UNIQUE (device_id, name);


--
-- Name: dcim_consoleport_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleport
    ADD CONSTRAINT dcim_consoleport_pkey PRIMARY KEY (id);


--
-- Name: dcim_consoleporttemplate_device_type_id_4181f4f26d97545e_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleporttemplate
    ADD CONSTRAINT dcim_consoleporttemplate_device_type_id_4181f4f26d97545e_uniq UNIQUE (device_type_id, name);


--
-- Name: dcim_consoleporttemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleporttemplate
    ADD CONSTRAINT dcim_consoleporttemplate_pkey PRIMARY KEY (id);


--
-- Name: dcim_consoleserverport_device_id_7736709af378c53f_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleserverport
    ADD CONSTRAINT dcim_consoleserverport_device_id_7736709af378c53f_uniq UNIQUE (device_id, name);


--
-- Name: dcim_consoleserverport_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleserverport
    ADD CONSTRAINT dcim_consoleserverport_pkey PRIMARY KEY (id);


--
-- Name: dcim_consoleserverporttempl_device_type_id_edd19c09550c93f_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleserverporttemplate
    ADD CONSTRAINT dcim_consoleserverporttempl_device_type_id_edd19c09550c93f_uniq UNIQUE (device_type_id, name);


--
-- Name: dcim_consoleserverporttemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_consoleserverporttemplate
    ADD CONSTRAINT dcim_consoleserverporttemplate_pkey PRIMARY KEY (id);


--
-- Name: dcim_device_name_203dd9298ce638c1_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_device_name_203dd9298ce638c1_uniq UNIQUE (name);


--
-- Name: dcim_device_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_device_pkey PRIMARY KEY (id);


--
-- Name: dcim_device_primary_ip_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_device_primary_ip_id_key UNIQUE (primary_ip_id);


--
-- Name: dcim_device_rack_id_51ba816b607befb4_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_device_rack_id_51ba816b607befb4_uniq UNIQUE (rack_id, "position", face);


--
-- Name: dcim_devicerole_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_devicerole
    ADD CONSTRAINT dcim_devicerole_name_key UNIQUE (name);


--
-- Name: dcim_devicerole_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_devicerole
    ADD CONSTRAINT dcim_devicerole_pkey PRIMARY KEY (id);


--
-- Name: dcim_devicerole_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_devicerole
    ADD CONSTRAINT dcim_devicerole_slug_key UNIQUE (slug);


--
-- Name: dcim_devicetype_manufacturer_id_1261ef49562adaa4_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_devicetype
    ADD CONSTRAINT dcim_devicetype_manufacturer_id_1261ef49562adaa4_uniq UNIQUE (manufacturer_id, slug);


--
-- Name: dcim_devicetype_manufacturer_id_1cfa2f3e364bcae3_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_devicetype
    ADD CONSTRAINT dcim_devicetype_manufacturer_id_1cfa2f3e364bcae3_uniq UNIQUE (manufacturer_id, model);


--
-- Name: dcim_devicetype_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_devicetype
    ADD CONSTRAINT dcim_devicetype_pkey PRIMARY KEY (id);


--
-- Name: dcim_interface_device_id_1a96eafe3cd9e3df_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_interface
    ADD CONSTRAINT dcim_interface_device_id_1a96eafe3cd9e3df_uniq UNIQUE (device_id, name);


--
-- Name: dcim_interface_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_interface
    ADD CONSTRAINT dcim_interface_pkey PRIMARY KEY (id);


--
-- Name: dcim_interfaceconnection_interface_a_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_interfaceconnection
    ADD CONSTRAINT dcim_interfaceconnection_interface_a_id_key UNIQUE (interface_a_id);


--
-- Name: dcim_interfaceconnection_interface_b_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_interfaceconnection
    ADD CONSTRAINT dcim_interfaceconnection_interface_b_id_key UNIQUE (interface_b_id);


--
-- Name: dcim_interfaceconnection_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_interfaceconnection
    ADD CONSTRAINT dcim_interfaceconnection_pkey PRIMARY KEY (id);


--
-- Name: dcim_interfacetemplate_device_type_id_7a05c4e376f93953_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_interfacetemplate
    ADD CONSTRAINT dcim_interfacetemplate_device_type_id_7a05c4e376f93953_uniq UNIQUE (device_type_id, name);


--
-- Name: dcim_interfacetemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_interfacetemplate
    ADD CONSTRAINT dcim_interfacetemplate_pkey PRIMARY KEY (id);


--
-- Name: dcim_manufacturer_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_manufacturer
    ADD CONSTRAINT dcim_manufacturer_name_key UNIQUE (name);


--
-- Name: dcim_manufacturer_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_manufacturer
    ADD CONSTRAINT dcim_manufacturer_pkey PRIMARY KEY (id);


--
-- Name: dcim_manufacturer_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_manufacturer
    ADD CONSTRAINT dcim_manufacturer_slug_key UNIQUE (slug);


--
-- Name: dcim_module_device_id_4d8292af_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_module
    ADD CONSTRAINT dcim_module_device_id_4d8292af_uniq UNIQUE (device_id, parent_id, name);


--
-- Name: dcim_module_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_module
    ADD CONSTRAINT dcim_module_pkey PRIMARY KEY (id);


--
-- Name: dcim_platform_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_platform
    ADD CONSTRAINT dcim_platform_name_key UNIQUE (name);


--
-- Name: dcim_platform_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_platform
    ADD CONSTRAINT dcim_platform_pkey PRIMARY KEY (id);


--
-- Name: dcim_platform_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_platform
    ADD CONSTRAINT dcim_platform_slug_key UNIQUE (slug);


--
-- Name: dcim_poweroutlet_device_id_7c22b6bb01a5ff2c_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_poweroutlet
    ADD CONSTRAINT dcim_poweroutlet_device_id_7c22b6bb01a5ff2c_uniq UNIQUE (device_id, name);


--
-- Name: dcim_poweroutlet_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_poweroutlet
    ADD CONSTRAINT dcim_poweroutlet_pkey PRIMARY KEY (id);


--
-- Name: dcim_poweroutlettemplate_device_type_id_6e69f9502b62feb8_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_poweroutlettemplate
    ADD CONSTRAINT dcim_poweroutlettemplate_device_type_id_6e69f9502b62feb8_uniq UNIQUE (device_type_id, name);


--
-- Name: dcim_poweroutlettemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_poweroutlettemplate
    ADD CONSTRAINT dcim_poweroutlettemplate_pkey PRIMARY KEY (id);


--
-- Name: dcim_powerport_device_id_75960a10f268db28_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_powerport
    ADD CONSTRAINT dcim_powerport_device_id_75960a10f268db28_uniq UNIQUE (device_id, name);


--
-- Name: dcim_powerport_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_powerport
    ADD CONSTRAINT dcim_powerport_pkey PRIMARY KEY (id);


--
-- Name: dcim_powerport_power_outlet_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_powerport
    ADD CONSTRAINT dcim_powerport_power_outlet_id_key UNIQUE (power_outlet_id);


--
-- Name: dcim_powerporttemplate_device_type_id_13286ca135e2f6c0_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_powerporttemplate
    ADD CONSTRAINT dcim_powerporttemplate_device_type_id_13286ca135e2f6c0_uniq UNIQUE (device_type_id, name);


--
-- Name: dcim_powerporttemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_powerporttemplate
    ADD CONSTRAINT dcim_powerporttemplate_pkey PRIMARY KEY (id);


--
-- Name: dcim_rack_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_rack
    ADD CONSTRAINT dcim_rack_pkey PRIMARY KEY (id);


--
-- Name: dcim_rack_site_id_30be92c1bfc1d387_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_rack
    ADD CONSTRAINT dcim_rack_site_id_30be92c1bfc1d387_uniq UNIQUE (site_id, name);


--
-- Name: dcim_rack_site_id_69909272a1e4c508_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_rack
    ADD CONSTRAINT dcim_rack_site_id_69909272a1e4c508_uniq UNIQUE (site_id, facility_id);


--
-- Name: dcim_rackgroup_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_rackgroup
    ADD CONSTRAINT dcim_rackgroup_pkey PRIMARY KEY (id);


--
-- Name: dcim_rackgroup_site_id_7fbfd118_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_rackgroup
    ADD CONSTRAINT dcim_rackgroup_site_id_7fbfd118_uniq UNIQUE (site_id, slug);


--
-- Name: dcim_rackgroup_site_id_c9bd921f_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_rackgroup
    ADD CONSTRAINT dcim_rackgroup_site_id_c9bd921f_uniq UNIQUE (site_id, name);


--
-- Name: dcim_site_name_78bc7a96590ccbd0_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_site
    ADD CONSTRAINT dcim_site_name_78bc7a96590ccbd0_uniq UNIQUE (name);


--
-- Name: dcim_site_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_site
    ADD CONSTRAINT dcim_site_pkey PRIMARY KEY (id);


--
-- Name: dcim_site_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY dcim_site
    ADD CONSTRAINT dcim_site_slug_key UNIQUE (slug);


--
-- Name: django_admin_log_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY django_admin_log
    ADD CONSTRAINT django_admin_log_pkey PRIMARY KEY (id);


--
-- Name: django_content_type_app_label_45f3b1d93ec8c61c_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY django_content_type
    ADD CONSTRAINT django_content_type_app_label_45f3b1d93ec8c61c_uniq UNIQUE (app_label, model);


--
-- Name: django_content_type_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY django_content_type
    ADD CONSTRAINT django_content_type_pkey PRIMARY KEY (id);


--
-- Name: django_migrations_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY django_migrations
    ADD CONSTRAINT django_migrations_pkey PRIMARY KEY (id);


--
-- Name: django_session_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY django_session
    ADD CONSTRAINT django_session_pkey PRIMARY KEY (session_key);


--
-- Name: extras_exporttemplate_content_type_id_7c9266ee8ac6d527_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY extras_exporttemplate
    ADD CONSTRAINT extras_exporttemplate_content_type_id_7c9266ee8ac6d527_uniq UNIQUE (content_type_id, name);


--
-- Name: extras_exporttemplate_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY extras_exporttemplate
    ADD CONSTRAINT extras_exporttemplate_pkey PRIMARY KEY (id);


--
-- Name: extras_graph_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY extras_graph
    ADD CONSTRAINT extras_graph_pkey PRIMARY KEY (id);


--
-- Name: extras_topologymap_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY extras_topologymap
    ADD CONSTRAINT extras_topologymap_name_key UNIQUE (name);


--
-- Name: extras_topologymap_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY extras_topologymap
    ADD CONSTRAINT extras_topologymap_pkey PRIMARY KEY (id);


--
-- Name: extras_topologymap_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY extras_topologymap
    ADD CONSTRAINT extras_topologymap_slug_key UNIQUE (slug);


--
-- Name: inet_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY inet
    ADD CONSTRAINT inet_pkey PRIMARY KEY (id);


--
-- Name: ipam_aggregate_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_aggregate
    ADD CONSTRAINT ipam_aggregate_pkey PRIMARY KEY (id);


--
-- Name: ipam_ipaddress_nat_inside_id_54e134739a4fce35_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_ipaddress
    ADD CONSTRAINT ipam_ipaddress_nat_inside_id_54e134739a4fce35_uniq UNIQUE (nat_inside_id);


--
-- Name: ipam_ipaddress_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_ipaddress
    ADD CONSTRAINT ipam_ipaddress_pkey PRIMARY KEY (id);


--
-- Name: ipam_prefix_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_prefix
    ADD CONSTRAINT ipam_prefix_pkey PRIMARY KEY (id);


--
-- Name: ipam_rir_name_189e93024f01ec65_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_rir
    ADD CONSTRAINT ipam_rir_name_189e93024f01ec65_uniq UNIQUE (name);


--
-- Name: ipam_rir_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_rir
    ADD CONSTRAINT ipam_rir_pkey PRIMARY KEY (id);


--
-- Name: ipam_rir_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_rir
    ADD CONSTRAINT ipam_rir_slug_key UNIQUE (slug);


--
-- Name: ipam_role_name_1f2da3fe0d1ed5cf_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_role
    ADD CONSTRAINT ipam_role_name_1f2da3fe0d1ed5cf_uniq UNIQUE (name);


--
-- Name: ipam_role_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_role
    ADD CONSTRAINT ipam_role_pkey PRIMARY KEY (id);


--
-- Name: ipam_role_slug_b1b7426c7eb1a07_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_role
    ADD CONSTRAINT ipam_role_slug_b1b7426c7eb1a07_uniq UNIQUE (slug);


--
-- Name: ipam_vlan_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_vlan
    ADD CONSTRAINT ipam_vlan_pkey PRIMARY KEY (id);


--
-- Name: ipam_vrf_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_vrf
    ADD CONSTRAINT ipam_vrf_pkey PRIMARY KEY (id);


--
-- Name: ipam_vrf_rd_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY ipam_vrf
    ADD CONSTRAINT ipam_vrf_rd_key UNIQUE (rd);


--
-- Name: mac_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY mac
    ADD CONSTRAINT mac_pkey PRIMARY KEY (id);


--
-- Name: nullcidr_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY nullcidr
    ADD CONSTRAINT nullcidr_pkey PRIMARY KEY (id);


--
-- Name: nullinet_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY nullinet
    ADD CONSTRAINT nullinet_pkey PRIMARY KEY (id);


--
-- Name: secrets_secret_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secret
    ADD CONSTRAINT secrets_secret_pkey PRIMARY KEY (id);


--
-- Name: secrets_secretrole_groups_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secretrole_groups
    ADD CONSTRAINT secrets_secretrole_groups_pkey PRIMARY KEY (id);


--
-- Name: secrets_secretrole_groups_secretrole_id_1c7f7ee5_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secretrole_groups
    ADD CONSTRAINT secrets_secretrole_groups_secretrole_id_1c7f7ee5_uniq UNIQUE (secretrole_id, group_id);


--
-- Name: secrets_secretrole_name_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secretrole
    ADD CONSTRAINT secrets_secretrole_name_key UNIQUE (name);


--
-- Name: secrets_secretrole_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secretrole
    ADD CONSTRAINT secrets_secretrole_pkey PRIMARY KEY (id);


--
-- Name: secrets_secretrole_slug_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secretrole
    ADD CONSTRAINT secrets_secretrole_slug_key UNIQUE (slug);


--
-- Name: secrets_secretrole_users_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secretrole_users
    ADD CONSTRAINT secrets_secretrole_users_pkey PRIMARY KEY (id);


--
-- Name: secrets_secretrole_users_secretrole_id_41832d38_uniq; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_secretrole_users
    ADD CONSTRAINT secrets_secretrole_users_secretrole_id_41832d38_uniq UNIQUE (secretrole_id, user_id);


--
-- Name: secrets_userkey_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_userkey
    ADD CONSTRAINT secrets_userkey_pkey PRIMARY KEY (id);


--
-- Name: secrets_userkey_user_id_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY secrets_userkey
    ADD CONSTRAINT secrets_userkey_user_id_key UNIQUE (user_id);


--
-- Name: uniquecidr_field_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY uniquecidr
    ADD CONSTRAINT uniquecidr_field_key UNIQUE (field);


--
-- Name: uniquecidr_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY uniquecidr
    ADD CONSTRAINT uniquecidr_pkey PRIMARY KEY (id);


--
-- Name: uniqueinet_field_key; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY uniqueinet
    ADD CONSTRAINT uniqueinet_field_key UNIQUE (field);


--
-- Name: uniqueinet_pkey; Type: CONSTRAINT; Schema: public; Owner: django; Tablespace: 
--

ALTER TABLE ONLY uniqueinet
    ADD CONSTRAINT uniqueinet_pkey PRIMARY KEY (id);


--
-- Name: auth_group_name_253ae2a6331666e8_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_group_name_253ae2a6331666e8_like ON auth_group USING btree (name varchar_pattern_ops);


--
-- Name: auth_group_permissions_0e939a4f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_group_permissions_0e939a4f ON auth_group_permissions USING btree (group_id);


--
-- Name: auth_group_permissions_8373b171; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_group_permissions_8373b171 ON auth_group_permissions USING btree (permission_id);


--
-- Name: auth_permission_417f1b1c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_permission_417f1b1c ON auth_permission USING btree (content_type_id);


--
-- Name: auth_user_groups_0e939a4f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_user_groups_0e939a4f ON auth_user_groups USING btree (group_id);


--
-- Name: auth_user_groups_e8701ad4; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_user_groups_e8701ad4 ON auth_user_groups USING btree (user_id);


--
-- Name: auth_user_user_permissions_8373b171; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_user_user_permissions_8373b171 ON auth_user_user_permissions USING btree (permission_id);


--
-- Name: auth_user_user_permissions_e8701ad4; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_user_user_permissions_e8701ad4 ON auth_user_user_permissions USING btree (user_id);


--
-- Name: auth_user_username_51b3b110094b8aae_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX auth_user_username_51b3b110094b8aae_like ON auth_user USING btree (username varchar_pattern_ops);


--
-- Name: circuits_circuit_32ca2ddc; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX circuits_circuit_32ca2ddc ON circuits_circuit USING btree (provider_id);


--
-- Name: circuits_circuit_9365d6e7; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX circuits_circuit_9365d6e7 ON circuits_circuit USING btree (site_id);


--
-- Name: circuits_circuit_94757cae; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX circuits_circuit_94757cae ON circuits_circuit USING btree (type_id);


--
-- Name: circuits_circuittype_name_1c2ade2dc0696954_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX circuits_circuittype_name_1c2ade2dc0696954_like ON circuits_circuittype USING btree (name varchar_pattern_ops);


--
-- Name: circuits_circuittype_slug_476ab74403291bbc_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX circuits_circuittype_slug_476ab74403291bbc_like ON circuits_circuittype USING btree (slug varchar_pattern_ops);


--
-- Name: circuits_provider_name_6edbf97e6646bc6d_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX circuits_provider_name_6edbf97e6646bc6d_like ON circuits_provider USING btree (name varchar_pattern_ops);


--
-- Name: circuits_provider_slug_14c10aece416912b_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX circuits_provider_slug_14c10aece416912b_like ON circuits_provider USING btree (slug varchar_pattern_ops);


--
-- Name: dcim_consoleport_9379346c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_consoleport_9379346c ON dcim_consoleport USING btree (device_id);


--
-- Name: dcim_consoleporttemplate_bddcf45f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_consoleporttemplate_bddcf45f ON dcim_consoleporttemplate USING btree (device_type_id);


--
-- Name: dcim_consoleserverport_9379346c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_consoleserverport_9379346c ON dcim_consoleserverport USING btree (device_id);


--
-- Name: dcim_consoleserverporttemplate_bddcf45f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_consoleserverporttemplate_bddcf45f ON dcim_consoleserverporttemplate USING btree (device_type_id);


--
-- Name: dcim_device_136ca3fc; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_device_136ca3fc ON dcim_device USING btree (device_role_id);


--
-- Name: dcim_device_21556361; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_device_21556361 ON dcim_device USING btree (rack_id);


--
-- Name: dcim_device_bddcf45f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_device_bddcf45f ON dcim_device USING btree (device_type_id);


--
-- Name: dcim_device_cb857215; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_device_cb857215 ON dcim_device USING btree (platform_id);


--
-- Name: dcim_devicerole_name_2ba786129816183_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_devicerole_name_2ba786129816183_like ON dcim_devicerole USING btree (name varchar_pattern_ops);


--
-- Name: dcim_devicetype_2dbcba41; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_devicetype_2dbcba41 ON dcim_devicetype USING btree (slug);


--
-- Name: dcim_devicetype_4d136c4a; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_devicetype_4d136c4a ON dcim_devicetype USING btree (manufacturer_id);


--
-- Name: dcim_interface_9379346c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_interface_9379346c ON dcim_interface USING btree (device_id);


--
-- Name: dcim_interfacetemplate_bddcf45f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_interfacetemplate_bddcf45f ON dcim_interfacetemplate USING btree (device_type_id);


--
-- Name: dcim_manufacturer_name_d0e87afc92d84ee_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_manufacturer_name_d0e87afc92d84ee_like ON dcim_manufacturer USING btree (name varchar_pattern_ops);


--
-- Name: dcim_module_6be37982; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_module_6be37982 ON dcim_module USING btree (parent_id);


--
-- Name: dcim_module_9379346c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_module_9379346c ON dcim_module USING btree (device_id);


--
-- Name: dcim_platform_name_79dfde6abeff3d4_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_platform_name_79dfde6abeff3d4_like ON dcim_platform USING btree (name varchar_pattern_ops);


--
-- Name: dcim_platform_slug_7c74a6b8ac58979c_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_platform_slug_7c74a6b8ac58979c_like ON dcim_platform USING btree (slug varchar_pattern_ops);


--
-- Name: dcim_poweroutlet_9379346c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_poweroutlet_9379346c ON dcim_poweroutlet USING btree (device_id);


--
-- Name: dcim_poweroutlettemplate_bddcf45f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_poweroutlettemplate_bddcf45f ON dcim_poweroutlettemplate USING btree (device_type_id);


--
-- Name: dcim_powerport_9379346c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_powerport_9379346c ON dcim_powerport USING btree (device_id);


--
-- Name: dcim_powerporttemplate_bddcf45f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_powerporttemplate_bddcf45f ON dcim_powerporttemplate USING btree (device_type_id);


--
-- Name: dcim_rack_0e939a4f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_rack_0e939a4f ON dcim_rack USING btree (group_id);


--
-- Name: dcim_rack_9365d6e7; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_rack_9365d6e7 ON dcim_rack USING btree (site_id);


--
-- Name: dcim_rackgroup_2dbcba41; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_rackgroup_2dbcba41 ON dcim_rackgroup USING btree (slug);


--
-- Name: dcim_rackgroup_9365d6e7; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_rackgroup_9365d6e7 ON dcim_rackgroup USING btree (site_id);


--
-- Name: dcim_rackgroup_slug_3f4582a7_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_rackgroup_slug_3f4582a7_like ON dcim_rackgroup USING btree (slug varchar_pattern_ops);


--
-- Name: dcim_site_slug_7e27fbff5c4239c8_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX dcim_site_slug_7e27fbff5c4239c8_like ON dcim_site USING btree (slug varchar_pattern_ops);


--
-- Name: django_admin_log_417f1b1c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX django_admin_log_417f1b1c ON django_admin_log USING btree (content_type_id);


--
-- Name: django_admin_log_e8701ad4; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX django_admin_log_e8701ad4 ON django_admin_log USING btree (user_id);


--
-- Name: django_session_de54fa62; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX django_session_de54fa62 ON django_session USING btree (expire_date);


--
-- Name: django_session_session_key_461cfeaa630ca218_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX django_session_session_key_461cfeaa630ca218_like ON django_session USING btree (session_key varchar_pattern_ops);


--
-- Name: extras_exporttemplate_417f1b1c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX extras_exporttemplate_417f1b1c ON extras_exporttemplate USING btree (content_type_id);


--
-- Name: extras_topologymap_9365d6e7; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX extras_topologymap_9365d6e7 ON extras_topologymap USING btree (site_id);


--
-- Name: extras_topologymap_name_f377ebf1_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX extras_topologymap_name_f377ebf1_like ON extras_topologymap USING btree (name varchar_pattern_ops);


--
-- Name: extras_topologymap_slug_9ba3d31e_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX extras_topologymap_slug_9ba3d31e_like ON extras_topologymap USING btree (slug varchar_pattern_ops);


--
-- Name: ipam_aggregate_rir_id_6b95f7cbf861b265_uniq; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_aggregate_rir_id_6b95f7cbf861b265_uniq ON ipam_aggregate USING btree (rir_id);


--
-- Name: ipam_ipaddress_0db30079; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_ipaddress_0db30079 ON ipam_ipaddress USING btree (vrf_id);


--
-- Name: ipam_ipaddress_455280ca; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_ipaddress_455280ca ON ipam_ipaddress USING btree (nat_inside_id);


--
-- Name: ipam_ipaddress_991706b3; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_ipaddress_991706b3 ON ipam_ipaddress USING btree (interface_id);


--
-- Name: ipam_prefix_0db30079; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_prefix_0db30079 ON ipam_prefix USING btree (vrf_id);


--
-- Name: ipam_prefix_84566833; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_prefix_84566833 ON ipam_prefix USING btree (role_id);


--
-- Name: ipam_prefix_9365d6e7; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_prefix_9365d6e7 ON ipam_prefix USING btree (site_id);


--
-- Name: ipam_prefix_cd1dc8b7; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_prefix_cd1dc8b7 ON ipam_prefix USING btree (vlan_id);


--
-- Name: ipam_rir_slug_416a41a245986cd_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_rir_slug_416a41a245986cd_like ON ipam_rir USING btree (slug varchar_pattern_ops);


--
-- Name: ipam_role_2dbcba41; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_role_2dbcba41 ON ipam_role USING btree (slug);


--
-- Name: ipam_vlan_84566833; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_vlan_84566833 ON ipam_vlan USING btree (role_id);


--
-- Name: ipam_vlan_9365d6e7; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX ipam_vlan_9365d6e7 ON ipam_vlan USING btree (site_id);


--
-- Name: secrets_secret_84566833; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secret_84566833 ON secrets_secret USING btree (role_id);


--
-- Name: secrets_secret_9379346c; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secret_9379346c ON secrets_secret USING btree (device_id);


--
-- Name: secrets_secretrole_groups_0e939a4f; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secretrole_groups_0e939a4f ON secrets_secretrole_groups USING btree (group_id);


--
-- Name: secrets_secretrole_groups_be893205; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secretrole_groups_be893205 ON secrets_secretrole_groups USING btree (secretrole_id);


--
-- Name: secrets_secretrole_name_7b6ee7a4_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secretrole_name_7b6ee7a4_like ON secrets_secretrole USING btree (name varchar_pattern_ops);


--
-- Name: secrets_secretrole_slug_a06c885e_like; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secretrole_slug_a06c885e_like ON secrets_secretrole USING btree (slug varchar_pattern_ops);


--
-- Name: secrets_secretrole_users_be893205; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secretrole_users_be893205 ON secrets_secretrole_users USING btree (secretrole_id);


--
-- Name: secrets_secretrole_users_e8701ad4; Type: INDEX; Schema: public; Owner: django; Tablespace: 
--

CREATE INDEX secrets_secretrole_users_e8701ad4 ON secrets_secretrole_users USING btree (user_id);


--
-- Name: auth_content_type_id_508cf46651277a81_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_permission
    ADD CONSTRAINT auth_content_type_id_508cf46651277a81_fk_django_content_type_id FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permissio_group_id_689710a9a73b7457_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permissio_group_id_689710a9a73b7457_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_group_permission_id_1f49ccbbdc69d2fc_fk_auth_permission_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_group_permissions
    ADD CONSTRAINT auth_group_permission_id_1f49ccbbdc69d2fc_fk_auth_permission_id FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user__permission_id_384b62483d7071f0_fk_auth_permission_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_user_user_permissions
    ADD CONSTRAINT auth_user__permission_id_384b62483d7071f0_fk_auth_permission_id FOREIGN KEY (permission_id) REFERENCES auth_permission(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups_group_id_33ac548dcf5f8e37_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_user_groups
    ADD CONSTRAINT auth_user_groups_group_id_33ac548dcf5f8e37_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_groups_user_id_4b5ed4ffdb8fd9b0_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_user_groups
    ADD CONSTRAINT auth_user_groups_user_id_4b5ed4ffdb8fd9b0_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: auth_user_user_permiss_user_id_7f0938558328534a_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY auth_user_user_permissions
    ADD CONSTRAINT auth_user_user_permiss_user_id_7f0938558328534a_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: circuits_c_provider_id_167247d72362b097_fk_circuits_provider_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY circuits_circuit
    ADD CONSTRAINT circuits_c_provider_id_167247d72362b097_fk_circuits_provider_id FOREIGN KEY (provider_id) REFERENCES circuits_provider(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: circuits_ci_type_id_1d69462c5f0198ee_fk_circuits_circuittype_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY circuits_circuit
    ADD CONSTRAINT circuits_ci_type_id_1d69462c5f0198ee_fk_circuits_circuittype_id FOREIGN KEY (type_id) REFERENCES circuits_circuittype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: circuits_circ_interface_id_a7a235094605e66_fk_dcim_interface_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY circuits_circuit
    ADD CONSTRAINT circuits_circ_interface_id_a7a235094605e66_fk_dcim_interface_id FOREIGN KEY (interface_id) REFERENCES dcim_interface(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: circuits_circuit_site_id_1fda25e8f4b8a5d_fk_dcim_site_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY circuits_circuit
    ADD CONSTRAINT circuits_circuit_site_id_1fda25e8f4b8a5d_fk_dcim_site_id FOREIGN KEY (site_id) REFERENCES dcim_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_co_cs_port_id_1f865a9aeca79c3_fk_dcim_consoleserverport_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleport
    ADD CONSTRAINT dcim_co_cs_port_id_1f865a9aeca79c3_fk_dcim_consoleserverport_id FOREIGN KEY (cs_port_id) REFERENCES dcim_consoleserverport(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_cons_device_type_id_2b0cd8d64161d670_fk_dcim_devicetype_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleporttemplate
    ADD CONSTRAINT dcim_cons_device_type_id_2b0cd8d64161d670_fk_dcim_devicetype_id FOREIGN KEY (device_type_id) REFERENCES dcim_devicetype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_conso_device_type_id_9b0ca867cae19a1_fk_dcim_devicetype_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleserverporttemplate
    ADD CONSTRAINT dcim_conso_device_type_id_9b0ca867cae19a1_fk_dcim_devicetype_id FOREIGN KEY (device_type_id) REFERENCES dcim_devicetype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_consoleport_device_id_29b9f8e27e9d6770_fk_dcim_device_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleport
    ADD CONSTRAINT dcim_consoleport_device_id_29b9f8e27e9d6770_fk_dcim_device_id FOREIGN KEY (device_id) REFERENCES dcim_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_consoleserver_device_id_511cd2919b14863f_fk_dcim_device_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_consoleserverport
    ADD CONSTRAINT dcim_consoleserver_device_id_511cd2919b14863f_fk_dcim_device_id FOREIGN KEY (device_id) REFERENCES dcim_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_d_manufacturer_id_579c553080e9dedc_fk_dcim_manufacturer_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_devicetype
    ADD CONSTRAINT dcim_d_manufacturer_id_579c553080e9dedc_fk_dcim_manufacturer_id FOREIGN KEY (manufacturer_id) REFERENCES dcim_manufacturer(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_devi_device_type_id_52445e10d85be955_fk_dcim_devicetype_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_devi_device_type_id_52445e10d85be955_fk_dcim_devicetype_id FOREIGN KEY (device_type_id) REFERENCES dcim_devicetype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_devic_device_role_id_56eba740fa716a1_fk_dcim_devicerole_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_devic_device_role_id_56eba740fa716a1_fk_dcim_devicerole_id FOREIGN KEY (device_role_id) REFERENCES dcim_devicerole(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_device_platform_id_23623cd01a633f9a_fk_dcim_platform_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_device_platform_id_23623cd01a633f9a_fk_dcim_platform_id FOREIGN KEY (platform_id) REFERENCES dcim_platform(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_device_primary_ip_id_584ce7bd0806540b_fk_ipam_ipaddress_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_device_primary_ip_id_584ce7bd0806540b_fk_ipam_ipaddress_id FOREIGN KEY (primary_ip_id) REFERENCES ipam_ipaddress(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_device_rack_id_6e66edde5ed2479a_fk_dcim_rack_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_device
    ADD CONSTRAINT dcim_device_rack_id_6e66edde5ed2479a_fk_dcim_rack_id FOREIGN KEY (rack_id) REFERENCES dcim_rack(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_inte_device_type_id_39b236aeb5adb9e5_fk_dcim_devicetype_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_interfacetemplate
    ADD CONSTRAINT dcim_inte_device_type_id_39b236aeb5adb9e5_fk_dcim_devicetype_id FOREIGN KEY (device_type_id) REFERENCES dcim_devicetype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_inter_interface_a_id_4a90ee91ee670fa1_fk_dcim_interface_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_interfaceconnection
    ADD CONSTRAINT dcim_inter_interface_a_id_4a90ee91ee670fa1_fk_dcim_interface_id FOREIGN KEY (interface_a_id) REFERENCES dcim_interface(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_inter_interface_b_id_1e536e3d7fa00862_fk_dcim_interface_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_interfaceconnection
    ADD CONSTRAINT dcim_inter_interface_b_id_1e536e3d7fa00862_fk_dcim_interface_id FOREIGN KEY (interface_b_id) REFERENCES dcim_interface(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_interface_device_id_cebcbb2c2f43d21_fk_dcim_device_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_interface
    ADD CONSTRAINT dcim_interface_device_id_cebcbb2c2f43d21_fk_dcim_device_id FOREIGN KEY (device_id) REFERENCES dcim_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_module_device_id_75c6e9c983691bed_fk_dcim_device_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_module
    ADD CONSTRAINT dcim_module_device_id_75c6e9c983691bed_fk_dcim_device_id FOREIGN KEY (device_id) REFERENCES dcim_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_module_parent_id_bb5d0341_fk_dcim_module_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_module
    ADD CONSTRAINT dcim_module_parent_id_bb5d0341_fk_dcim_module_id FOREIGN KEY (parent_id) REFERENCES dcim_module(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_po_power_outlet_id_4099940c71613091_fk_dcim_poweroutlet_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_powerport
    ADD CONSTRAINT dcim_po_power_outlet_id_4099940c71613091_fk_dcim_poweroutlet_id FOREIGN KEY (power_outlet_id) REFERENCES dcim_poweroutlet(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_powe_device_type_id_384e9ac366036152_fk_dcim_devicetype_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_powerporttemplate
    ADD CONSTRAINT dcim_powe_device_type_id_384e9ac366036152_fk_dcim_devicetype_id FOREIGN KEY (device_type_id) REFERENCES dcim_devicetype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_powe_device_type_id_7807d6dc359b9cd6_fk_dcim_devicetype_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_poweroutlettemplate
    ADD CONSTRAINT dcim_powe_device_type_id_7807d6dc359b9cd6_fk_dcim_devicetype_id FOREIGN KEY (device_type_id) REFERENCES dcim_devicetype(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_poweroutlet_device_id_5e311222f8451092_fk_dcim_device_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_poweroutlet
    ADD CONSTRAINT dcim_poweroutlet_device_id_5e311222f8451092_fk_dcim_device_id FOREIGN KEY (device_id) REFERENCES dcim_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_powerport_device_id_67713503b63c2a2a_fk_dcim_device_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_powerport
    ADD CONSTRAINT dcim_powerport_device_id_67713503b63c2a2a_fk_dcim_device_id FOREIGN KEY (device_id) REFERENCES dcim_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_rack_group_id_44e90ea9_fk_dcim_rackgroup_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_rack
    ADD CONSTRAINT dcim_rack_group_id_44e90ea9_fk_dcim_rackgroup_id FOREIGN KEY (group_id) REFERENCES dcim_rackgroup(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_rack_site_id_5d7ccc420afb55f5_fk_dcim_site_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_rack
    ADD CONSTRAINT dcim_rack_site_id_5d7ccc420afb55f5_fk_dcim_site_id FOREIGN KEY (site_id) REFERENCES dcim_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: dcim_rackgroup_site_id_13520e89_fk_dcim_site_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY dcim_rackgroup
    ADD CONSTRAINT dcim_rackgroup_site_id_13520e89_fk_dcim_site_id FOREIGN KEY (site_id) REFERENCES dcim_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: djan_content_type_id_697914295151027a_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY django_admin_log
    ADD CONSTRAINT djan_content_type_id_697914295151027a_fk_django_content_type_id FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: django_admin_log_user_id_52fdd58701c5f563_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY django_admin_log
    ADD CONSTRAINT django_admin_log_user_id_52fdd58701c5f563_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extr_content_type_id_3d11dce08b0c7e23_fk_django_content_type_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY extras_exporttemplate
    ADD CONSTRAINT extr_content_type_id_3d11dce08b0c7e23_fk_django_content_type_id FOREIGN KEY (content_type_id) REFERENCES django_content_type(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: extras_topologymap_site_id_b56b3ceb_fk_dcim_site_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY extras_topologymap
    ADD CONSTRAINT extras_topologymap_site_id_b56b3ceb_fk_dcim_site_id FOREIGN KEY (site_id) REFERENCES dcim_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_aggregate_rir_id_6b95f7cbf861b265_fk_ipam_rir_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_aggregate
    ADD CONSTRAINT ipam_aggregate_rir_id_6b95f7cbf861b265_fk_ipam_rir_id FOREIGN KEY (rir_id) REFERENCES ipam_rir(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_ipaddr_nat_inside_id_54e134739a4fce35_fk_ipam_ipaddress_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_ipaddress
    ADD CONSTRAINT ipam_ipaddr_nat_inside_id_54e134739a4fce35_fk_ipam_ipaddress_id FOREIGN KEY (nat_inside_id) REFERENCES ipam_ipaddress(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_ipaddre_interface_id_1453a9dc6dd4107f_fk_dcim_interface_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_ipaddress
    ADD CONSTRAINT ipam_ipaddre_interface_id_1453a9dc6dd4107f_fk_dcim_interface_id FOREIGN KEY (interface_id) REFERENCES dcim_interface(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_ipaddress_vrf_id_7961a6a27bac9dc0_fk_ipam_vrf_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_ipaddress
    ADD CONSTRAINT ipam_ipaddress_vrf_id_7961a6a27bac9dc0_fk_ipam_vrf_id FOREIGN KEY (vrf_id) REFERENCES ipam_vrf(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_prefix_role_id_176ef537da785ba5_fk_ipam_role_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_prefix
    ADD CONSTRAINT ipam_prefix_role_id_176ef537da785ba5_fk_ipam_role_id FOREIGN KEY (role_id) REFERENCES ipam_role(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_prefix_site_id_1256d3efdf9f08e8_fk_dcim_site_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_prefix
    ADD CONSTRAINT ipam_prefix_site_id_1256d3efdf9f08e8_fk_dcim_site_id FOREIGN KEY (site_id) REFERENCES dcim_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_prefix_vlan_id_46c10e1ba4efd5ae_fk_ipam_vlan_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_prefix
    ADD CONSTRAINT ipam_prefix_vlan_id_46c10e1ba4efd5ae_fk_ipam_vlan_id FOREIGN KEY (vlan_id) REFERENCES ipam_vlan(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_prefix_vrf_id_6a821d8b02f9f14c_fk_ipam_vrf_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_prefix
    ADD CONSTRAINT ipam_prefix_vrf_id_6a821d8b02f9f14c_fk_ipam_vrf_id FOREIGN KEY (vrf_id) REFERENCES ipam_vrf(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_vlan_role_id_61511bbc81bb1474_fk_ipam_role_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_vlan
    ADD CONSTRAINT ipam_vlan_role_id_61511bbc81bb1474_fk_ipam_role_id FOREIGN KEY (role_id) REFERENCES ipam_role(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: ipam_vlan_site_id_3d425e66fe6edb31_fk_dcim_site_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY ipam_vlan
    ADD CONSTRAINT ipam_vlan_site_id_3d425e66fe6edb31_fk_dcim_site_id FOREIGN KEY (site_id) REFERENCES dcim_site(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: secrets_secret_device_id_c7c13124_fk_dcim_device_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secret
    ADD CONSTRAINT secrets_secret_device_id_c7c13124_fk_dcim_device_id FOREIGN KEY (device_id) REFERENCES dcim_device(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: secrets_secret_role_id_39d9347f_fk_secrets_secretrole_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secret
    ADD CONSTRAINT secrets_secret_role_id_39d9347f_fk_secrets_secretrole_id FOREIGN KEY (role_id) REFERENCES secrets_secretrole(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: secrets_secretr_secretrole_id_3cf0338b_fk_secrets_secretrole_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secretrole_groups
    ADD CONSTRAINT secrets_secretr_secretrole_id_3cf0338b_fk_secrets_secretrole_id FOREIGN KEY (secretrole_id) REFERENCES secrets_secretrole(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: secrets_secretr_secretrole_id_d2eac298_fk_secrets_secretrole_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secretrole_users
    ADD CONSTRAINT secrets_secretr_secretrole_id_d2eac298_fk_secrets_secretrole_id FOREIGN KEY (secretrole_id) REFERENCES secrets_secretrole(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: secrets_secretrole_groups_group_id_a687dd10_fk_auth_group_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secretrole_groups
    ADD CONSTRAINT secrets_secretrole_groups_group_id_a687dd10_fk_auth_group_id FOREIGN KEY (group_id) REFERENCES auth_group(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: secrets_secretrole_users_user_id_25be95ad_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_secretrole_users
    ADD CONSTRAINT secrets_secretrole_users_user_id_25be95ad_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: secrets_userkey_user_id_13ada46b_fk_auth_user_id; Type: FK CONSTRAINT; Schema: public; Owner: django
--

ALTER TABLE ONLY secrets_userkey
    ADD CONSTRAINT secrets_userkey_user_id_13ada46b_fk_auth_user_id FOREIGN KEY (user_id) REFERENCES auth_user(id) DEFERRABLE INITIALLY DEFERRED;


--
-- Name: public; Type: ACL; Schema: -; Owner: postgres
--

REVOKE ALL ON SCHEMA public FROM PUBLIC;
REVOKE ALL ON SCHEMA public FROM postgres;
GRANT ALL ON SCHEMA public TO postgres;
GRANT ALL ON SCHEMA public TO PUBLIC;


--
-- PostgreSQL database dump complete
--

