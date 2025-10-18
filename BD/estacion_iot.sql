-- phpMyAdmin SQL Dump
-- version 5.2.1
-- https://www.phpmyadmin.net/
--
-- Servidor: 127.0.0.1
-- Tiempo de generación: 18-10-2025 a las 18:30:50
-- Versión del servidor: 10.4.32-MariaDB
-- Versión de PHP: 8.2.12

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
START TRANSACTION;
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Base de datos: `estacion_iot`
--

-- --------------------------------------------------------

--
-- Estructura de tabla para la tabla `lectura`
--

CREATE TABLE `lectura` (
  `id` int(11) NOT NULL,
  `temperatura` float DEFAULT NULL,
  `humedad` float DEFAULT NULL,
  `co2` float DEFAULT NULL,
  `fecha` datetime DEFAULT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_general_ci;

--
-- Volcado de datos para la tabla `lectura`
--

INSERT INTO `lectura` (`id`, `temperatura`, `humedad`, `co2`, `fecha`) VALUES
(11, 18.7, 65, 5, '2025-10-18 09:35:31'),
(12, 18.6, 65, 6, '2025-10-18 09:35:41'),
(13, 18.6, 65, 6, '2025-10-18 09:35:51'),
(14, 18.6, 64, 5, '2025-10-18 09:36:01'),
(15, 18.6, 64, 5, '2025-10-18 09:36:11'),
(16, 18.6, 64, 4, '2025-10-18 09:36:21'),
(17, 18.6, 64, 4, '2025-10-18 09:36:31'),
(18, 18.6, 64, 5, '2025-10-18 09:36:41'),
(19, 18.6, 64, 4, '2025-10-18 09:36:51'),
(20, 18.6, 64, 3, '2025-10-18 09:37:01'),
(21, 19, 64, 3, '2025-10-18 09:37:11'),
(22, 19, 64, 3, '2025-10-18 09:37:21'),
(23, 19, 64, 3, '2025-10-18 09:37:32'),
(24, 19, 63, 3, '2025-10-18 09:37:41'),
(25, 19, 63, 3, '2025-10-18 09:37:51'),
(26, 19, 63, 3, '2025-10-18 09:38:01'),
(27, 19, 63, 3, '2025-10-18 09:38:11'),
(28, 18.9, 62, 3, '2025-10-18 09:38:21'),
(29, 19, 62, 3, '2025-10-18 09:38:31'),
(30, 18.9, 62, 3, '2025-10-18 09:38:41'),
(31, 18.7, 62, 3, '2025-10-18 09:38:51'),
(32, 18.7, 62, 3, '2025-10-18 09:39:01'),
(33, 18.8, 63, 3, '2025-10-18 09:39:11'),
(34, 18.9, 63, 3, '2025-10-18 09:39:21'),
(35, 18.8, 62, 0, '2025-10-18 09:39:31'),
(36, 19, 63, 3, '2025-10-18 09:39:41'),
(37, 19, 63, 3, '2025-10-18 09:39:51'),
(38, 19, 63, 2, '2025-10-18 09:40:01'),
(39, 19, 62, 2, '2025-10-18 09:40:11'),
(40, 19, 62, 2, '2025-10-18 09:40:21'),
(41, 19, 62, 2, '2025-10-18 09:40:31'),
(42, 19, 62, 2, '2025-10-18 09:40:41'),
(43, 19, 62, 2, '2025-10-18 09:40:51'),
(44, 19, 62, 2, '2025-10-18 09:41:01'),
(45, 19, 61, 2, '2025-10-18 09:41:11'),
(46, 19, 61, 2, '2025-10-18 09:41:21'),
(47, 19, 61, 2, '2025-10-18 09:41:31'),
(48, 19, 61, 2, '2025-10-18 09:41:41'),
(49, 19, 61, 2, '2025-10-18 09:41:51'),
(50, 19, 61, 2, '2025-10-18 09:42:01'),
(51, 19, 61, 2, '2025-10-18 09:42:11'),
(52, 19, 60, 2, '2025-10-18 09:42:21'),
(53, 19, 60, 2, '2025-10-18 09:42:31'),
(54, 19, 60, 2, '2025-10-18 09:42:41'),
(55, 19, 60, 2, '2025-10-18 09:42:51'),
(56, 19, 60, 2, '2025-10-18 09:43:01'),
(57, 19, 60, 2, '2025-10-18 09:43:11'),
(58, 19, 60, 2, '2025-10-18 09:43:21'),
(59, 19, 60, 2, '2025-10-18 09:43:31'),
(60, 19, 60, 2, '2025-10-18 09:43:41');

--
-- Índices para tablas volcadas
--

--
-- Indices de la tabla `lectura`
--
ALTER TABLE `lectura`
  ADD PRIMARY KEY (`id`);

--
-- AUTO_INCREMENT de las tablas volcadas
--

--
-- AUTO_INCREMENT de la tabla `lectura`
--
ALTER TABLE `lectura`
  MODIFY `id` int(11) NOT NULL AUTO_INCREMENT, AUTO_INCREMENT=61;
COMMIT;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
