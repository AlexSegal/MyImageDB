-- phpMyAdmin SQL Dump
-- version 4.4.10
-- http://www.phpmyadmin.net
--
-- Host: localhost
-- Generation Time: Oct 31, 2018 at 06:39 AM
-- Server version: 5.5.43-MariaDB
-- PHP Version: 5.5.26

SET SQL_MODE = "NO_AUTO_VALUE_ON_ZERO";
SET time_zone = "+00:00";


/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!40101 SET NAMES utf8mb4 */;

--
-- Database: `my_image_db`
--

-- --------------------------------------------------------

--
-- Table structure for table `image_files`
--

CREATE TABLE IF NOT EXISTS `image_files` (
  `imageID` int(11) unsigned NOT NULL,
  `path` text NOT NULL,
  `format` enum('jpg','png','tif','exr','gif') NOT NULL,
  `num_channels` tinyint(3) unsigned NOT NULL DEFAULT '0',
  `pixel_type` tinytext NOT NULL,
  `orig_timestamp` datetime NOT NULL,
  `last_updated` timestamp NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `hash` tinytext NOT NULL,
  `colorspace` enum('sRGB','AdobeRGB') NOT NULL DEFAULT 'sRGB',
  `width` int(10) unsigned NOT NULL,
  `height` int(10) unsigned NOT NULL,
  `frame_aspect` float NOT NULL DEFAULT '1',
  `active` tinyint(1) NOT NULL DEFAULT '1'
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `mip_level0`
--

CREATE TABLE IF NOT EXISTS `mip_level0` (
  `mip_level0ID` int(11) unsigned NOT NULL,
  `red` float NOT NULL DEFAULT '0',
  `green` float NOT NULL DEFAULT '0',
  `blue` float NOT NULL DEFAULT '0',
  `imageID` int(11) unsigned NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `mip_level1`
--

CREATE TABLE IF NOT EXISTS `mip_level1` (
  `mip_level1ID` int(11) unsigned NOT NULL,
  `red0` float NOT NULL DEFAULT '0',
  `green0` float NOT NULL DEFAULT '0',
  `blue0` float NOT NULL DEFAULT '0',
  `red1` float NOT NULL DEFAULT '0',
  `green1` float NOT NULL DEFAULT '0',
  `blue1` float NOT NULL DEFAULT '0',
  `red2` float NOT NULL DEFAULT '0',
  `green2` float NOT NULL DEFAULT '0',
  `blue2` float NOT NULL DEFAULT '0',
  `red3` float NOT NULL DEFAULT '0',
  `green3` float NOT NULL DEFAULT '0',
  `blue3` float NOT NULL DEFAULT '0',
  `imageID` int(11) unsigned NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `mip_level2`
--

CREATE TABLE IF NOT EXISTS `mip_level2` (
  `mip_level2ID` int(11) unsigned NOT NULL,
  `red00` float NOT NULL DEFAULT '0',
  `green00` float NOT NULL DEFAULT '0',
  `blue00` float NOT NULL DEFAULT '0',
  `red01` float NOT NULL DEFAULT '0',
  `green01` float NOT NULL DEFAULT '0',
  `blue01` float NOT NULL DEFAULT '0',
  `red02` float NOT NULL DEFAULT '0',
  `green02` float NOT NULL DEFAULT '0',
  `blue02` float NOT NULL DEFAULT '0',
  `red03` float NOT NULL DEFAULT '0',
  `green03` float NOT NULL DEFAULT '0',
  `blue03` float NOT NULL DEFAULT '0',
  `red04` float NOT NULL DEFAULT '0',
  `green04` float NOT NULL DEFAULT '0',
  `blue04` float NOT NULL DEFAULT '0',
  `red05` float NOT NULL DEFAULT '0',
  `green05` float NOT NULL DEFAULT '0',
  `blue05` float NOT NULL DEFAULT '0',
  `red06` float NOT NULL DEFAULT '0',
  `green06` float NOT NULL DEFAULT '0',
  `blue06` float NOT NULL DEFAULT '0',
  `red07` float NOT NULL DEFAULT '0',
  `green07` float NOT NULL DEFAULT '0',
  `blue07` float NOT NULL DEFAULT '0',
  `red08` float NOT NULL DEFAULT '0',
  `green08` float NOT NULL DEFAULT '0',
  `blue08` float NOT NULL DEFAULT '0',
  `red09` float NOT NULL DEFAULT '0',
  `green09` float NOT NULL DEFAULT '0',
  `blue09` float NOT NULL DEFAULT '0',
  `red10` float NOT NULL DEFAULT '0',
  `green10` float NOT NULL DEFAULT '0',
  `blue10` float NOT NULL DEFAULT '0',
  `red11` float NOT NULL DEFAULT '0',
  `green11` float NOT NULL DEFAULT '0',
  `blue11` float NOT NULL DEFAULT '0',
  `red12` float NOT NULL DEFAULT '0',
  `green12` float NOT NULL DEFAULT '0',
  `blue12` float NOT NULL DEFAULT '0',
  `red13` float NOT NULL DEFAULT '0',
  `green13` float NOT NULL DEFAULT '0',
  `blue13` float NOT NULL DEFAULT '0',
  `red14` float NOT NULL DEFAULT '0',
  `green14` float NOT NULL DEFAULT '0',
  `blue14` float NOT NULL DEFAULT '0',
  `red15` float NOT NULL DEFAULT '0',
  `green15` float NOT NULL DEFAULT '0',
  `blue15` float NOT NULL DEFAULT '0',
  `imageID` int(11) unsigned NOT NULL
) ENGINE=InnoDB DEFAULT CHARSET=utf8;

-- --------------------------------------------------------

--
-- Table structure for table `thumbnails`
--

CREATE TABLE IF NOT EXISTS `thumbnails` (
  `thumbnailID` int(11) unsigned NOT NULL,
  `width` smallint(5) unsigned NOT NULL DEFAULT '0',
  `height` smallint(5) unsigned NOT NULL DEFAULT '0',
  `imageID` int(11) unsigned NOT NULL,
  `thumbnail_format` enum('jpg','png','tif','exr','gif') CHARACTER SET latin1 DEFAULT 'png',
  `thumbnail_image` blob
) ENGINE=InnoDB DEFAULT CHARSET=ascii COLLATE=ascii_bin ROW_FORMAT=COMPACT;

--
-- Indexes for dumped tables
--

--
-- Indexes for table `image_files`
--
ALTER TABLE `image_files`
  ADD PRIMARY KEY (`imageID`),
  ADD UNIQUE KEY `path` (`path`(255)),
  ADD KEY `format` (`format`),
  ADD KEY `hash_idx` (`hash`(64)),
  ADD KEY `pixel_type_idx` (`pixel_type`(10)),
  ADD KEY `size_idx` (`width`,`height`,`frame_aspect`),
  ADD KEY `timestamp_idx` (`last_updated`,`orig_timestamp`),
  ADD KEY `num_channels_idx` (`num_channels`),
  ADD KEY `active_idx` (`active`);

--
-- Indexes for table `mip_level0`
--
ALTER TABLE `mip_level0`
  ADD PRIMARY KEY (`mip_level0ID`) USING BTREE,
  ADD UNIQUE KEY `imageID_UNIQUE` (`imageID`),
  ADD KEY `rgb_idx` (`red`,`green`,`blue`),
  ADD KEY `imageID` (`imageID`) USING BTREE;

--
-- Indexes for table `mip_level1`
--
ALTER TABLE `mip_level1`
  ADD PRIMARY KEY (`mip_level1ID`),
  ADD UNIQUE KEY `imageID_UNIQUE` (`imageID`),
  ADD KEY `rgb_idx` (`red0`,`green0`,`blue0`,`red1`,`green1`,`blue1`,`red2`,`green2`,`blue2`,`red3`,`green3`,`blue3`),
  ADD KEY `imageID_idx` (`imageID`),
  ADD KEY `imageID` (`imageID`);

--
-- Indexes for table `mip_level2`
--
ALTER TABLE `mip_level2`
  ADD PRIMARY KEY (`mip_level2ID`),
  ADD UNIQUE KEY `imageID_UNIQUE` (`imageID`),
  ADD KEY `rgb_idx0` (`red00`,`green00`,`blue00`,`red01`,`green01`,`blue01`,`red02`,`green02`,`blue02`,`red03`,`green03`,`blue03`,`red04`,`green04`,`blue04`,`red05`,`green05`,`blue05`,`red06`,`green06`,`blue06`,`red07`,`green07`,`blue07`),
  ADD KEY `rgb_idx1` (`red08`,`green08`,`blue08`,`red09`,`green09`,`blue09`,`red10`,`green10`,`blue10`,`red11`,`green11`,`blue11`,`red12`,`green12`,`blue12`,`red13`,`green13`,`blue13`,`red14`,`green14`,`blue14`,`red15`,`green15`,`blue15`),
  ADD KEY `mip_level2_ibfk_1` (`imageID`);

--
-- Indexes for table `thumbnails`
--
ALTER TABLE `thumbnails`
  ADD PRIMARY KEY (`thumbnailID`),
  ADD UNIQUE KEY `imageID_UNIQUE` (`imageID`),
  ADD KEY `imageID` (`imageID`);

--
-- AUTO_INCREMENT for dumped tables
--

--
-- AUTO_INCREMENT for table `image_files`
--
ALTER TABLE `image_files`
  MODIFY `imageID` int(11) unsigned NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `mip_level0`
--
ALTER TABLE `mip_level0`
  MODIFY `mip_level0ID` int(11) unsigned NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `mip_level1`
--
ALTER TABLE `mip_level1`
  MODIFY `mip_level1ID` int(11) unsigned NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `mip_level2`
--
ALTER TABLE `mip_level2`
  MODIFY `mip_level2ID` int(11) unsigned NOT NULL AUTO_INCREMENT;
--
-- AUTO_INCREMENT for table `thumbnails`
--
ALTER TABLE `thumbnails`
  MODIFY `thumbnailID` int(11) unsigned NOT NULL AUTO_INCREMENT;
--
-- Constraints for dumped tables
--

--
-- Constraints for table `mip_level0`
--
ALTER TABLE `mip_level0`
  ADD CONSTRAINT `mip_level0_ibfk_1` FOREIGN KEY (`imageID`) REFERENCES `image_files` (`imageID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `mip_level1`
--
ALTER TABLE `mip_level1`
  ADD CONSTRAINT `mip_level1_ibfk_1` FOREIGN KEY (`imageID`) REFERENCES `image_files` (`imageID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `mip_level2`
--
ALTER TABLE `mip_level2`
  ADD CONSTRAINT `mip_level2_ibfk_1` FOREIGN KEY (`imageID`) REFERENCES `image_files` (`imageID`) ON DELETE CASCADE ON UPDATE CASCADE;

--
-- Constraints for table `thumbnails`
--
ALTER TABLE `thumbnails`
  ADD CONSTRAINT `thumb_image_id_ifk` FOREIGN KEY (`imageID`) REFERENCES `image_files` (`imageID`) ON DELETE CASCADE ON UPDATE CASCADE;

/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
