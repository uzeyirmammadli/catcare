--
-- PostgreSQL database dump
--

-- Dumped from database version 15.1
-- Dumped by pg_dump version 15.1

SET statement_timeout = 0;
SET lock_timeout = 0;
SET idle_in_transaction_session_timeout = 0;
SET client_encoding = 'UTF8';
SET standard_conforming_strings = on;
SELECT pg_catalog.set_config('search_path', '', false);
SET check_function_bodies = false;
SET xmloption = content;
SET client_min_messages = warning;
SET row_security = off;

ALTER TABLE IF EXISTS ONLY public.comment DROP CONSTRAINT IF EXISTS comment_user_id_fkey;
ALTER TABLE IF EXISTS ONLY public."case" DROP CONSTRAINT IF EXISTS case_user_id_fkey1;
DROP INDEX IF EXISTS public.ix_user_username;
ALTER TABLE IF EXISTS ONLY public."user" DROP CONSTRAINT IF EXISTS user_pkey;
ALTER TABLE IF EXISTS ONLY public.comment DROP CONSTRAINT IF EXISTS comment_pkey;
ALTER TABLE IF EXISTS ONLY public."case" DROP CONSTRAINT IF EXISTS case_pkey1;
ALTER TABLE IF EXISTS public."user" ALTER COLUMN id DROP DEFAULT;
ALTER TABLE IF EXISTS public.comment ALTER COLUMN id DROP DEFAULT;
DROP SEQUENCE IF EXISTS public.user_id_seq;
DROP TABLE IF EXISTS public."user";
DROP SEQUENCE IF EXISTS public.comment_id_seq;
DROP TABLE IF EXISTS public.comment;
DROP TABLE IF EXISTS public."case";
SET default_tablespace = '';

SET default_table_access_method = heap;

--
-- Name: case; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."case" (
    id character varying(36) NOT NULL,
    photo character varying(200),
    location character varying(100) NOT NULL,
    need character varying(200),
    status character varying(20),
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    user_id integer NOT NULL,
    resolution_notes text
);


--
-- Name: comment; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public.comment (
    id integer NOT NULL,
    content text NOT NULL,
    created_at timestamp without time zone,
    updated_at timestamp without time zone,
    case_id character varying(36) NOT NULL,
    user_id integer NOT NULL
);


--
-- Name: comment_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.comment_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: comment_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.comment_id_seq OWNED BY public.comment.id;


--
-- Name: user; Type: TABLE; Schema: public; Owner: -
--

CREATE TABLE public."user" (
    id integer NOT NULL,
    username character varying(64) NOT NULL,
    password_hash character varying(255) NOT NULL
);


--
-- Name: user_id_seq; Type: SEQUENCE; Schema: public; Owner: -
--

CREATE SEQUENCE public.user_id_seq
    AS integer
    START WITH 1
    INCREMENT BY 1
    NO MINVALUE
    NO MAXVALUE
    CACHE 1;


--
-- Name: user_id_seq; Type: SEQUENCE OWNED BY; Schema: public; Owner: -
--

ALTER SEQUENCE public.user_id_seq OWNED BY public."user".id;


--
-- Name: comment id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment ALTER COLUMN id SET DEFAULT nextval('public.comment_id_seq'::regclass);


--
-- Name: user id; Type: DEFAULT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user" ALTER COLUMN id SET DEFAULT nextval('public.user_id_seq'::regclass);


--
-- Data for Name: case; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."case" (id, photo, location, need, status, created_at, updated_at, user_id, resolution_notes) FROM stdin;
f2ac9028-e84a-4e32-9c11-7fa5e5cc4779	5c05da3b-2117-4b5b-a87e-599e268cb21a_nilperi.jpg	Baku	other	OPEN	2024-10-29 07:13:01.365447	2024-10-29 07:39:50.58633	1	\N
84d84295-3d09-4387-a816-6d28f9ab5744	rebus.jpg	Baku	medical	OPEN	2024-10-29 07:09:13.426885	2024-10-29 07:47:57.97875	1	\N
89b3899d-2689-4769-8c4d-ef74530b18cb	e1da4402-ccc1-405b-b5cb-08e45cde2d90_SUSA2.jpeg	28 may	shelter	OPEN	2024-10-31 12:47:09.602874	2024-10-31 12:47:09.602876	1	\N
45270ca1-015f-41bc-87d2-babda5c1dfa5	9e7ff73d-b695-46b1-b7ce-cc348f59c853_Screenshot from 2024-11-25 12-21-48.png	Mayakovski	medical	RESOLVED	2024-12-10 12:55:09.972781	2024-12-11 12:58:50.60808	1	\N
7714ced7-f632-4eab-af56-54d814596ed5	737a5ef0-3aae-4bb3-92c2-d7122431f52f_fanat.jpeg	Mayakovski	shelter	OPEN	2024-10-29 16:48:56.364578	2024-10-29 16:48:56.36458	1	\N
0e10318f-3cbe-4c67-8f3f-7c2963785eba	d8888b5e-8596-465b-948e-9e673e03cc53_bad day.jpeg	28 may	medical	OPEN	2024-10-29 17:57:29.86144	2024-10-29 17:57:29.861443	1	\N
b97b3409-e2f8-4657-805c-8a86446d8238	Screenshot_from_2024-10-29_12-34-33.png	Mayakovski	medical	OPEN	2024-10-29 16:47:58.084307	2024-10-29 18:10:50.348296	1	\N
43c0eab4-d639-4329-a0d5-6f0a9f171726	fanat.jpeg	28 may	other	OPEN	2024-10-29 16:33:14.11203	2024-10-29 18:24:25.27098	1	\N
eac86b78-485f-4b80-b5e7-ce53c797c155	5bdbb369-b3e2-4d93-ab08-6285a38d4030_nilperi5.jpg	28 may	medical	OPEN	2024-10-31 13:18:25.107614	2024-10-31 13:18:25.107616	1	\N
9d1e104b-c4bb-4d28-a958-4c07d8c9d22e	7aee62b9-6e69-43ef-a7c3-9e7d9f84b782_barlas.jpeg	Baku	food	OPEN	2024-10-31 13:23:21.161919	2024-10-31 13:23:21.161921	1	\N
d0fb5df8-b678-46c3-b526-98277294963f	16ce6396-1d81-4dcd-90c1-976974868fa3_SUSA.jpeg	Mayakovski	medical	OPEN	2024-11-02 12:35:35.751546	2024-11-02 12:35:35.751558	1	\N
ad6f3103-ca45-4ca4-943b-73e4cb65a65c	4957585c-da0e-4477-820d-42716f662736_nilperi.jpg	Mayakovski	food	OPEN	2024-11-04 08:20:53.222994	2024-11-04 08:20:53.222997	1	\N
3bd25357-87a6-4998-9a33-9a975e030c66	93efdcf2-8ec4-47a1-8800-0dab3e898f1e_FrUFlHgXoAkhzzy.jpeg	Ramana	medical	OPEN	2024-10-30 09:07:39.745196	2024-11-07 07:21:00.356634	1	\N
2bc868d1-e6b2-4371-8d14-a9990253cfd3	Screenshot_from_2024-11-21_15-28-03.png	28 may	shelter	OPEN	2024-12-11 13:20:29.593109	2024-12-11 13:21:19.881958	1	\N
6d6dc843-ae8c-4695-83f1-693397bbd673	ba1b3bba-2348-47fa-8c49-245c9057b75e_Screenshot_from_2024-12-06_13-40-08.png	Mayakovski	food	OPEN	2024-12-11 13:21:47.247921	2024-12-11 13:21:47.247923	1	\N
369be798-4c32-48db-995a-63d57cae6a6e	03f206e7-b0be-49a3-9342-4446172a0d88_Screenshot_from_2024-11-18_22-27-13.png	Nasirov	rescue	OPEN	2024-12-12 08:56:27.831967	2024-12-12 08:56:27.83197	1	\N
c2dfa203-45f4-40f5-8a6c-6cd52f6678be	a9d4e800-a86e-4ceb-ab18-ca1dfb416671_Screenshot_from_2024-11-19_13-03-41.png	28 may	food	OPEN	2024-12-12 08:58:57.719835	2024-12-12 08:58:57.719837	1	\N
108e7d5c-185c-4050-8ffc-9856fa3ecf26	fd3464f0-a27c-4f0b-b5e1-0cc66e63cf9e_SUSA.jpeg	Nasirov	food	RESOLVED	2024-11-04 10:17:20.512929	2024-12-06 12:57:58.856916	1	\N
681d1d23-60df-4db1-8dc5-51a330e8738a	06062f5b-482b-419d-a782-5d5cd5f0f572_Screenshot from 2024-11-28 17-53-33.png	Mayakovski	shelter	OPEN	2024-12-10 12:22:35.982836	2024-12-10 12:22:35.982844	1	\N
7abdfac3-db97-4ba8-982d-62b363994123	d9c77840-513a-4010-a206-8d5bd8716641_Screenshot from 2024-12-06 13-40-08.png	28 may	shelter	OPEN	2024-12-10 12:23:57.69891	2024-12-10 12:23:57.698914	1	\N
4d00c59a-e8d2-4391-9ace-9eb7d4e1bd47	94344d87-7fef-4453-8478-7a9fea5fbc59_Screenshot from 2024-12-03 14-08-26.png	Montin	medical	OPEN	2024-12-10 12:48:45.561084	2024-12-10 12:48:45.561086	1	\N
53023cea-27a2-4e95-8dff-3da4442ce51b	684ad9f4-b1e5-4098-99e1-7d5c97305635_Screenshot from 2024-11-28 17-46-59.png	Nasirov	rescue	OPEN	2024-12-10 12:50:49.267713	2024-12-10 12:50:49.267716	1	\N
\.


--
-- Data for Name: comment; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public.comment (id, content, created_at, updated_at, case_id, user_id) FROM stdin;
9	hello	2024-10-29 17:30:52.027544	2024-10-29 17:30:52.027546	b97b3409-e2f8-4657-805c-8a86446d8238	1
\.


--
-- Data for Name: user; Type: TABLE DATA; Schema: public; Owner: -
--

COPY public."user" (id, username, password_hash) FROM stdin;
1	uzeyirmammadlee@gmail.com	scrypt:32768:8:1$6sBAlOzMpL7h7LwV$54935e4821c2dfc6c4659535682ff93d1ad818685f4a9d206c9cd59942e6b20bdda3c59a4607fad5183cb72eba0b9b3ead179246ef1787034bcee3e5d9b37f3e
2	uzeyir.mmlee@gmail.com	scrypt:32768:8:1$zBL1wErrrwDVBDkQ$ebd7e9387d47bbc312140c589cae2e9404dff16cacc26850cd987cb01f192add5e3751e8f134b35c2eb16c9a33aca7834e743e0a7c61ebfe81ec06bc14e313ee
3	aygunpenceliyeva@gmail.com	scrypt:32768:8:1$G8DOZ5YHbHkHBOLl$e979395a5e10d282bd91eef1719acf5f3c86ea94363870b5981c7569170f9e08c656e952ca6c9de8f1f689c849e48f7e95e0845b10427fb08a707206d0388374
\.


--
-- Name: comment_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.comment_id_seq', 15, true);


--
-- Name: user_id_seq; Type: SEQUENCE SET; Schema: public; Owner: -
--

SELECT pg_catalog.setval('public.user_id_seq', 3, true);


--
-- Name: case case_pkey1; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."case"
    ADD CONSTRAINT case_pkey1 PRIMARY KEY (id);


--
-- Name: comment comment_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_pkey PRIMARY KEY (id);


--
-- Name: user user_pkey; Type: CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."user"
    ADD CONSTRAINT user_pkey PRIMARY KEY (id);


--
-- Name: ix_user_username; Type: INDEX; Schema: public; Owner: -
--

CREATE UNIQUE INDEX ix_user_username ON public."user" USING btree (username);


--
-- Name: case case_user_id_fkey1; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public."case"
    ADD CONSTRAINT case_user_id_fkey1 FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- Name: comment comment_user_id_fkey; Type: FK CONSTRAINT; Schema: public; Owner: -
--

ALTER TABLE ONLY public.comment
    ADD CONSTRAINT comment_user_id_fkey FOREIGN KEY (user_id) REFERENCES public."user"(id);


--
-- PostgreSQL database dump complete
--

